from __future__ import annotations

import html
import json
import re
import urllib.parse
from io import StringIO
from typing import Iterable, Sequence

import bs4
from google.auth import impersonated_credentials

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import Alert
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import unix_now

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.data_models import (
    CASE_DATA_STATUS_VAL_NAME_MAP,
    CASE_PRIORITY_VAL_NAME_MAP,
    CaseDetails,
)
from TIPCommon.exceptions import NotFoundError
from TIPCommon.rest.auth import DEFAULT_CONTEXT_SCOPE, get_impersonated_credentials
from TIPCommon.rest.soar_api import get_workflow_instance_card
from TIPCommon.soar_ops import get_user_by_id
from TIPCommon.transformation import removesuffix
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none

from scc_enterprise.core.SCCEnterpriseConsts import (
    CASE_URL_TEMPLATE,
    CLOUD_PROVIDER_AWS,
    CLOUD_PROVIDER_AZURE,
    CLOUD_PROVIDER_GCP,
    CLOUD_PROVIDER_OTHER,
    NOT_AVAILABLE,
    OOTB_AUTH_ID_SCCE,
    OOTB_AUTH_KEY_SCCE,
    V_EMOJI,
    X_EMOJI,
    MUTE_EMOJI,
    FINDING_SEVERITY_COLOR_MAPPING,
)
from scc_enterprise.core.SCCEnterpriseDatamodels import (
    CloudProviderEnum,
    FindingContext,
    SOARCaseDetailsForSCC,
    WorkflowInstance,
)
from scc_enterprise.core.SCCEnterpriseExceptions import ProjectNotFound


__scce_sa_email = None


def get_scce_sa_email(chronicle_soar: ChronicleSOAR) -> str:
    """
    Retrieves the SCC Enterprise Service Account Client Email

    Args:
        chronicle_soar (ChronicleSOAR): Chronicle SOAR SDK instance

    Returns:
        str: Service Account Client Email
    """
    global __scce_sa_email
    if __scce_sa_email is None:
        __scce_sa_email = chronicle_soar.get_context_property(
            context_type=DEFAULT_CONTEXT_SCOPE,
            identifier=OOTB_AUTH_ID_SCCE,
            property_key=OOTB_AUTH_KEY_SCCE,
        )
    return __scce_sa_email


def parse_project_from_sa(service_account_email: str) -> str:
    """Parse the project name out of the service account email

    Args:
        service_account_email (str): Service Account email

    Returns:
        str: project name of the service account

    raises:
        ProjectNotFound: Could not parse the project name ouf of the SA email
    """
    try:
        res = re.findall(r"@([\w0-9\-_]+).", service_account_email)
        return res[0]

    except (TypeError, IndexError) as e:
        raise ProjectNotFound(
            "Project name could not be found in Service Account email: "
            f"{str(service_account_email)}"
        ) from e


def get_scce_default_project_id(chronicle_soar: ChronicleSOAR) -> str:
    """Parse the project ID from the default SCC Enterprise SA client email

    Args:
        chronicle_soar (ChronicleSOAR): Chronicle SOAR SDK instance

    Returns:
        str: project ID from the default SCC Enterprise SA client email
    """
    return parse_project_from_sa(get_scce_sa_email(chronicle_soar))


def get_scce_tenant_credentials(
    chronicle_soar: ChronicleSOAR,
    target_scopes: Sequence[str] | None = None,
    quota_project_id: str | None = None,
) -> impersonated_credentials.Credentials:
    """Get the Google Security Command Center tenant short-lived
    service account credentials of the SCC Enterprise instance

    Args:
        chronicle_soar (TIPCommon.types.ChronicleSOAR):
            ChronicleSOAR SDK object
        target_scopes (Sequence[str] | None):
            Scopes to request during the authorization grant.
        quota_project_id (Optional[str] | None):
            The project ID used for quota and billing.
            This project may be different from the project used to
            create the credentials.

    Returns:
        impersonated_credentials.Credentials:
            Google Security Command Center tenant short-lived
            service account credentials
    """
    scc_sa_email = get_scce_sa_email(chronicle_soar)
    if is_empty_string_or_none(scc_sa_email):
        raise NotFoundError(
            "Security Command Center tenant short-lived service account email "
            "not found in SOAR context"
        )
    return get_impersonated_credentials(
        target_principal=scc_sa_email,
        target_scopes=target_scopes,
        quota_project_id=quota_project_id,
    )


def load_findings_context(
    findings_context_str: str | None,
) -> tuple[str | None, set[FindingContext]]:
    """Load findings data from json string

    Args:
        findings_context_str: Findings context string

    Returns:
        [str, set]: The instance deployment url, set of FindingContext objects
    """
    if not findings_context_str:
        return None, set()

    findings_context_json = json.loads(findings_context_str)
    instance_url = findings_context_json.get("instance_url")
    finding_context_list = findings_context_json.get("finding_context_list", [])
    return instance_url, {
        FindingContext(**finding_event_data)
        for finding_event_data in finding_context_list
    }


def create_scc_finding_state_json(
    findings_context: Iterable[FindingContext], instance_url: str
) -> SingleJson:
    return {
        "last_update_time": unix_now(),
        "instance_url": instance_url,
        "finding_context_list": FindingContext.prepare_json_sorted(findings_context),
    }


def construct_soar_case_url(case_id: int, platform_url: str) -> str:
    """Construct Chronicle SOAR case URL

    Args:
        case_id: The case's ID
        platform_url: The platform's URL

    Returns:
        str: A URL to the case view
    """
    platform_url = platform_url.strip()
    if platform_url.endswith("/#/"):
        platform_url = removesuffix(platform_url, "/#/")

    elif platform_url.endswith("/#"):
        platform_url = removesuffix(platform_url, "/#")

    elif platform_url.endswith("/"):
        platform_url = removesuffix(platform_url, "/")

    return CASE_URL_TEMPLATE.format(ui_root=platform_url, case_id=case_id)


def escape_url(s: str) -> str:
    """Escape a string to be put in a URL

    Args:
        s (str): The string to escape

    Returns:
        str: The escaped string
    """
    return s if not isinstance(s, (str, bytes)) else urllib.parse.quote(s)


def escape_url_plus(s: str) -> str:
    """Escape a string to be put in a URL.

    Escape reserved chars with quote_plus including front-slashes '/'

    Args:
        s (str): The string to escape

    Returns:
        str: The escaped string
    """
    return s if not isinstance(s, (str, bytes)) else urllib.parse.quote_plus(s)


# Move to TIPCommon
def add_params_to_url(url: str, params: SingleJson) -> str:
    """
    Takes a URL and key-value pairs of query parameters,
    and return the URL with the parameters inside

    Args:
        url (str): URL
        params (dict[str, Any]): key-value pairs of query parameters

    Returns:
        str: URL with query params inside (url-encoded)
    """
    parsed_url = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed_url.query)
    query.update(params)
    parsed_url = parsed_url._replace(query=urllib.parse.urlencode(query))
    return str(urllib.parse.urlunparse(parsed_url))


def is_soar_support_scce(soar_sdk: ChronicleSOAR) -> bool:
    """
    Checks if the SCC Enterprise related scripts are supported by SOAR Platform and SDK

    Args:
        soar_sdk (ChronicleSOAR): The SOAR SDK Object

    Returns:
        bool: `True` if platform Supports SCC Enterprise. `False` Otherwise
    """
    return (
        # check for Action & Job SDK objects
        hasattr(soar_sdk, "get_alerts_ticket_ids_by_case_id")
        # check for Connector SDK object
        or hasattr(soar_sdk, "get_case_status_by_id")
    )


def soar_supports_scce_phase_2(soar_sdk: ChronicleSOAR) -> bool:
    """
    Checks if the SCC Enterprise related scripts are supported by SOAR Platform and SDK

    Args:
        soar_sdk (ChronicleSOAR): The SOAR SDK Object

    Returns:
        bool: `True` if platform Supports SCC Enterprise. `False` Otherwise
    """
    return hasattr(soar_sdk, "platform_url")


def get_first_event_data(chronicle_soar: SiemplifyAction) -> SingleJson:
    """Get the additional data of an event of an alert of the current case

    Args:
        chronicle_soar (SiemplifyAction): SDK object

    Returns:
        SingleJson: Additional data dict of the event
    """
    return getattr(
        next(iter(getattr(chronicle_soar.current_alert, "security_events", [])), None),
        "additional_properties",
        {},
    )


def get_alert_source_group_identifier(alert: Alert) -> str:
    return alert.additional_properties["SourceGroupingIdentifier"]


def get_cloud_provider_from_source_group_id(source_group_id: str) -> CloudProviderEnum:
    """Get the current alert's cloud provider from the source grouping ID

    Args:
        source_group_id: An alert's source group identifier

    Returns:
        CloudProviderEnum: The corresponding cloud provider enum object

    Raises:
        ValueError - if no cloud provider is found in the source group identifier
    """
    source_group_id = source_group_id.upper()
    if CLOUD_PROVIDER_GCP in source_group_id:
        return CloudProviderEnum.GCP

    if CLOUD_PROVIDER_AWS in source_group_id:
        return CloudProviderEnum.AWS

    if CLOUD_PROVIDER_AZURE in source_group_id:
        return CloudProviderEnum.AZURE

    if CLOUD_PROVIDER_OTHER in source_group_id:
        return CloudProviderEnum.OTHER

    raise ValueError(
        "The current alert's source grouping identifier doesn't contain a "
        f'known cloud provider: "{source_group_id}"'
    )


def get_finding_value_by_key(finding_name: str, key: str) -> str | None:
    """Extract a specific value from a finding name/ID by a key.

    Examples:
        >>> finding_id = 'organizations/87623487/sources/92874/findings/0ssc53'
        >>> get_finding_value_by_key(finding_id, 'organizations')
        '87623487'
        >>> get_finding_value_by_key(finding_id, 'Some Key')
        None

    Args:
        finding_name: The finding's name
            (e.g. 'organizations/876234872/sources/928374/findings/0se7556sc')
        key: The key to get the value of (e.g. 'organizations' | 'sources')

    Returns:
        None if key isn't found in finding_name else the value of the key
    """
    if not key.endswith("/"):
        key += "/"

    i = finding_name.find(key)
    if i == -1:
        return None

    i += len(key)
    return finding_name[i:].split("/", maxsplit=1)[0]


def build_case_details_for_scc(
    soar_job: SiemplifyJob, case: CaseDetails
) -> SOARCaseDetailsForSCC:
    """Create a new external info case object based on case details

    Args:
        soar_job: SiemplifyJob instance
        case: All case details that the ext data will be updated from

    Returns:
        A new SOARCaseDetailsForSCC object to update the ext scc data with
    """
    mod_time = case.modification_time_unix_time_ms // NUM_OF_MILLI_IN_SEC

    sla = case.stage_sla.sla_expiration_time
    sla = sla // NUM_OF_MILLI_IN_SEC if sla is not None else NOT_AVAILABLE

    assignee = case.assigned_user
    user = get_user_by_id(soar_job, case.assigned_user)
    if user is not None:
        assignee = f"{user.first_name} {user.last_name}".strip()

    return SOARCaseDetailsForSCC(
        assignees=assignee,
        external_uid=str(case.id_),
        status=CASE_DATA_STATUS_VAL_NAME_MAP[case.status],
        external_system_update_time=mod_time,
        case_uri=construct_soar_case_url(
            case_id=case.id_, platform_url=soar_job.platform_url
        ),
        case_sla=sla,
        case_priority=CASE_PRIORITY_VAL_NAME_MAP[case.priority],
    )


def create_finding_page_link(
    finding_name: str, chronicle_soar_platform_url: str
) -> str:
    """Create a URL that links to an SCC finding page

    Args:
        finding_name (str): The finding's name/id
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        str: A link to the finding's page
    """
    return (
        f"{chronicle_soar_platform_url}posture/findings"
        f"?name={escape_url_plus(finding_name)}"
    )


def create_resource_link(resource_name: str, chronicle_soar_platform_url: str) -> str:
    """Create a URL that links to an Asset Inventory resource page
    Args:
        resource_name: The resource's name
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        The full URL to the resource/asset page
    """
    return (
        f"{chronicle_soar_platform_url}posture/resources/tabs/gcp"
        f"?name={escape_url_plus(resource_name)}"
    )


def create_html_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    if findings_state_context and not findings_state_context[0].is_cloud_provider_gcp:
        return create_non_gcp_html_table(
            findings_state_context, chronicle_soar_platform_url
        )

    return create_gcp_html_table(findings_state_context, chronicle_soar_platform_url)


def create_jwm_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    if findings_state_context and not findings_state_context[0].is_cloud_provider_gcp:
        return create_non_gcp_jwm_table(
            findings_state_context, chronicle_soar_platform_url
        )

    return create_gcp_jwm_table(findings_state_context, chronicle_soar_platform_url)


def create_gcp_html_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    """Create a finding summary HTML table

    Args:
        findings_state_context (list[FindingContext]): The finding state object
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        str: A populated HTML table structured to contain all findings data
    """
    # language=html
    table_html = (
        "<p><strong>Impacted Resources</strong></p>\n"
        '<table class="main-table">\n'
        "  <thead>\n"
        "    <tr>\n"
        '      <th id="resource-name">Resource Name</th>\n'
        '      <th id="state">Status</th>\n'
        '      <th id="latest-severity">Severity</th>\n'
        '      <th id="tc_count">Related TCs</th>\n'
        '      <th id="finding">Source</th>\n'
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        "    {table_rows}\n"
        "  </tbody>\n"
        "</table>\n"
    )

    table_row = (
        "<tr>\n"
        "  <td>\n"
        '    <a class="link text"\n'
        '      href="{resource_link}"\n'
        '      target="_blank">{resource_name}</a>\n'
        "  </td>\n"
        "  <td>\n"
        "    {status}\n"
        "  </td>\n"
        "  <td>\n"
        "    {severity}\n"
        "  </td>\n"
        "  <td>\n"
        '    <span class="text">{tc_count}</span>\n'
        "  </td>\n"
        "  <td>\n"
        '    <a class="link text"\n'
        '      href="{finding_link}"\n'
        '      target="_blank">Explore</a>\n'
        "  </td>\n"
        "</tr>\n"
    )

    table_rows = StringIO()
    for finding in findings_state_context:
        _set_html_status_color(finding)

        if finding.aps_score is None:
            finding.aps_score = NOT_AVAILABLE

        finding_link = create_finding_page_link(
            finding_name=finding.finding_id,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )
        resource_link = create_resource_link(
            resource_name=finding.resource_name,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )

        filled_row = table_row.format(
            resource_name=finding.resource_name,
            resource_link=resource_link,
            severity=_get_html_severity(finding.severity),
            aps_score=finding.aps_score,
            status=finding.status,
            finding_link=finding_link,
            tc_count=finding.tc_count or 0,
        )
        table_rows.write(f"{filled_row.strip()}\n")

    return table_html.format(table_rows=table_rows.getvalue().strip()).strip()


def create_non_gcp_html_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    """Create a finding summary HTML table

    Args:
        findings_state_context (list[FindingContext]): The finding state object
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        str: A populated HTML table structured to contain all findings data
    """
    # language=html
    table_html = (
        "<p><strong>Impacted Resources</strong></p>\n"
        '<table class="main-table">\n'
        "  <thead>\n"
        "    <tr>\n"
        '      <th id="resource-name">Resource Name</th>\n'
        '      <th id="state">Status</th>\n'
        '      <th id="latest-severity">Severity</th>\n'
        '      <th id="tc_count">Related TCs</th>\n'
        '      <th id="finding">Source</th>\n'
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        "    {table_rows}\n"
        "  </tbody>\n"
        "</table>\n"
    )

    table_row = (
        "<tr>\n"
        "  <td>\n"
        '    <span class="text">{resource_name}</span>\n'
        "  </td>\n"
        "  <td>\n"
        "    {status}\n"
        "  </td>\n"
        "  <td>\n"
        "    {severity}\n"
        "  </td>\n"
        "  <td>\n"
        '    <span class="text">{tc_count}</span>\n'
        "  </td>\n"
        "  <td>\n"
        '    <a class="link text"\n'
        '      href="{finding_link}"\n'
        '      target="_blank">Explore</a>\n'
        "  </td>\n"
        "</tr>\n"
    )

    table_rows = StringIO()
    for finding in findings_state_context:
        _set_html_status_color(finding)

        if finding.aps_score is None:
            finding.aps_score = NOT_AVAILABLE

        finding_link = create_finding_page_link(
            finding_name=finding.finding_id,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )

        filled_row = table_row.format(
            resource_name=finding.resource_name,
            severity=_get_html_severity(finding.severity),
            aps_score=finding.aps_score,
            status=finding.status,
            finding_link=finding_link,
            tc_count=finding.tc_count or 0,
        )
        table_rows.write(f"{filled_row.strip()}\n")

    return table_html.format(table_rows=table_rows.getvalue().strip()).strip()


def create_gcp_jwm_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    """Create a finding summary Jira Wiki table

    Args:
        findings_state_context (list[FindingContext]): The finding state object
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        str: A populated Jira Wiki table structured to contain all findings data
    """
    table_markup = (
        "||Resource Name||Status||Severity||Related TCs||Source||\n{table_rows}"
    )
    table_row = (
        "|[{resource_name}|{resource_link}]"
        "|{status}"
        "|{severity}"
        "|{tc_count}"
        "|[Explore|{finding_link}]|"
    )

    table_rows = StringIO()
    for finding in findings_state_context:
        _set_jwm_status_color(finding)

        if finding.aps_score is None:
            finding.aps_score = NOT_AVAILABLE

        resource_link = create_resource_link(
            resource_name=finding.resource_name,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )
        finding_link = create_finding_page_link(
            finding_name=finding.finding_id,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )

        filled_row = table_row.format(
            resource_name=finding.resource_name,
            resource_link=resource_link,
            severity=_get_jwm_severity(finding.severity),
            aps_score=finding.aps_score,
            status=finding.status,
            finding_link=finding_link,
            tc_count=finding.tc_count or 0,
        )
        table_rows.write(f"{filled_row.strip()}\n")

    return table_markup.format(table_rows=table_rows.getvalue().strip()).strip()


def create_non_gcp_jwm_table(
    findings_state_context: list[FindingContext], chronicle_soar_platform_url: str
) -> str:
    """Create a finding summary Jira Wiki table

    Args:
        findings_state_context (list[FindingContext]): The finding state object
        chronicle_soar_platform_url (str): Chronicle SOAR platform url

    Returns:
        str: A populated Jira Wiki table structured to contain all findings data
    """
    table_markup = (
        "||Resource Name||Status||Severity||Related TCs||Source||\n{table_rows}"
    )
    table_row = (
        "|{resource_name}"
        "|{status}"
        "|{severity}"
        "|{tc_count}"
        "|[Explore|{finding_link}]|"
    )

    table_rows = StringIO()
    for finding in findings_state_context:
        _set_jwm_status_color(finding)

        if finding.aps_score is None:
            finding.aps_score = NOT_AVAILABLE

        finding_link = create_finding_page_link(
            finding_name=finding.finding_id,
            chronicle_soar_platform_url=chronicle_soar_platform_url,
        )

        filled_row = table_row.format(
            resource_name=finding.resource_name,
            severity=_get_jwm_severity(finding.severity),
            aps_score=finding.aps_score,
            status=finding.status,
            finding_link=finding_link,
            tc_count=finding.tc_count or 0,
        )
        table_rows.write(f"{filled_row.strip()}\n")

    return table_markup.format(table_rows=table_rows.getvalue().strip()).strip()


def update_html_desc_table(table: str, description: str) -> str:
    """Update a ticket's html description with a new table

    Args:
        table: The new html table the description should be updated with
        description: The html description which table should be updated

    Returns:
        str: A new html description updated with the provided table
    """
    soup = bs4.BeautifulSoup(description, features="html.parser")
    table_div = soup.find("div", {"id": "main-table"})
    table_div.clear()
    table_div.append(table)

    return html.unescape(str(soup))


def update_jira_wiki_desc_table(table: str, description: str) -> str:
    """Update a ticket's jira wiki description with a new table

    Args:
        table: The new jira wiki table the description should be updated with
        description: The jira wiki description which table should be updated

    Returns:
        str: A new jira wiki description updated with the provided table
    """
    start_anchor = "{anchor:resource_table_start}"
    end_anchor = "{anchor:resource_table_end}"
    table_start_index = description.find(start_anchor) + len(start_anchor)
    table_end_index = description.rfind(end_anchor)
    if table_end_index == -1 or table_start_index == -1:
        raise ValueError(
            "Couldn't find end or start resource table anchor! "
            f"start anchor index: {table_start_index}, "
            f"end anchor index: {table_end_index}"
        )

    return (
        f"{description[:table_start_index]}\n"
        f"{table}\n"
        f"{description[table_end_index:]}"
    )


def _set_html_status_color(finding: FindingContext) -> None:
    status_style = ""
    if finding.status is not None:
        if finding.status.upper() == "ACTIVE" and finding.mute == "MUTED":
            finding.status = "MUTED"

        elif finding.status.upper() == "ACTIVE":
            status_style = ' style="color: red"'

        elif finding.status.upper() == "INACTIVE":
            status_style = ' style="color: green"'
            finding.status = "CLOSED"

    finding.status = f'<span class="text"{status_style}>{finding.status}</span>'


def _set_jwm_status_color(finding: FindingContext) -> None:
    status_color = ""
    if finding.status is not None:
        if finding.status.upper() == "ACTIVE" and finding.mute == "MUTED":
            finding.status = f"{MUTE_EMOJI} MUTED"

        elif finding.status.upper() == "ACTIVE":
            status_color = "{color:red}"
            finding.status = f"{X_EMOJI} ACTIVE"

        elif finding.status.upper() == "INACTIVE":
            status_color = "{color:green}"
            finding.status = f"{V_EMOJI} CLOSED"

    if status_color:
        finding.status = f"{status_color}{finding.status}{{color}}"


def _get_html_severity(finding_severity: str) -> str:
    """Get html for severity with corresponding color

    Args:
        finding_severity (str): finding severity

    Returns:
        (str) html severity
    """
    return (
        (
            f'<span class="text" style="color: '
            f"{FINDING_SEVERITY_COLOR_MAPPING.get(finding_severity.lower())}"
            f'">{finding_severity.capitalize()}</span>'
        )
        if finding_severity
        else ""
    )


def _get_jwm_severity(finding_severity: str) -> str:
    """Get jwm for severity with corresponding color

    Args:
        finding_severity (str): finding severity

    Returns:
        (str) jwm severity
    """
    return (
        (
            f"{{color:{FINDING_SEVERITY_COLOR_MAPPING.get(finding_severity.lower())}}}"
            f"{finding_severity.capitalize()}"
            f"{{color}}"
        )
        if finding_severity
        else ""
    )


# Move to TIPCommon
def get_workflow_instances(
    chronicle_soar: ChronicleSOAR, case_id: str, alert_identifier: str
) -> list[WorkflowInstance]:
    """Get workflow instances for a specific alert.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        case_id (int | str) The case id to fetch workflow cards
        alert_identifier (str) The alert identifier to fetch workflow cards

    Returns:
        (list[WorkflowInstance]): The case details object

    Raises:
        requests.HTTPError: If failed to request or request status is not 200
        json.JSONDecoderError: If parsing the response fails
    """
    workflow_cards = get_workflow_instance_card(
        chronicle_soar=chronicle_soar,
        case_id=case_id,
        alert_identifier=alert_identifier,
    )

    return [
        WorkflowInstance.from_json(workflow_instance_json)
        for workflow_instance_json in workflow_cards
    ]
