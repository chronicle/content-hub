# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
from urllib.parse import urljoin

from requests import HTTPError, Response
from SiemplifyDataModel import Attachment

from ..consts import DEFAULT_ENVIRONMENT
from ..data_models import (
    AlertEvent,
    AttachmentMetadata,
    CaseDetails,
    CaseWallAttachment,
    ConnectorCard,
    CreateEntity,
    CustomField,
    CustomFieldValue,
    EmailTemplate,
    EntityCard,
    EventCard,
    Insight,
    InstalledIntegrationInstance,
    UserDetails,
)
from ..exceptions import InternalJSONDecoderError
from ..types import ChronicleSOAR, SingleJson
from ..utils import get_sdk_api_uri, none_to_default_value, safe_json_for_204
from .soar_platform_clients.api_client_factory import get_soar_client
from .soar_platform_clients.legacy_soar_api import LegacySoarApi


class SoarApiServerError(Exception):
    """Errors from Chronicle SOAR's API calls to the server"""


def _validate_expand_parameters(**kwargs):
    """Validates that expand parameters do not contain the wildcard "*".

    Args:
        **kwargs: keyword arguments where key is the param name and value is the list.

    Raises:
        ValueError: If any of the expand parameters contains "*".

    """
    for param_name, expand_list in kwargs.items():
        if expand_list and "*" in expand_list:
            raise ValueError(
                f"Using '*' for '{param_name}' is not allowed. "
                "Please specify the exact fields to expand."
            )


def validate_response(
    response: Response,
    validate_json: bool = False,
) -> None:
    """Validate response and get it as a JSON

    Args:
        response (requests.Response): The response to validate

    Raises:
        HTTPError: If the response status code is pointing on some failure
        InternalJSONDecoderError: If the response failed to be parsed as JSON

    """
    try:
        response.raise_for_status()

        if validate_json:
            response.json()

    except HTTPError as he:
        raise HTTPError(f"An error happened while requesting API, {he}", response=he.response)

    except json.JSONDecodeError as je:
        raise InternalJSONDecoderError(
            f"Failed to parse response as JSON.\nError: {je}\nRaw response: {response.text}",
        )


# ==== GET ==== #
def get_case_overview_details(
    chronicle_soar: ChronicleSOAR,
    case_id: int | str,
    *,
    case_expand: list[str] | None = None,
    alert_expand: list[str] | None = None,
) -> CaseDetails:
    """Get case overview details with explicit expand separation.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int | str): The ID of the case.
        case_expand (list[str] | None): Fields to expand on the case object.
        alert_expand (list[str] | None): Fields to expand on the alerts within the case.

    Returns:
        CaseDetails: An object containing the case overview details.

    """
    _validate_expand_parameters(case_expand=case_expand, alert_expand=alert_expand)
    api = get_soar_client(chronicle_soar)
    p = api.params

    p.case_id = case_id
    p.case_expand = case_expand
    p.alert_expand = alert_expand

    return CaseDetails.from_json(api.get_case_overview_details())


def get_installed_jobs(
    chronicle_soar: ChronicleSOAR,
    job_instance_id: int | None = None,
) -> list[SingleJson] | SingleJson:
    """Retrieve a list of environment action definition files.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        job_instance_id (int | None): Job ID to filter the results.

    Returns:
        (list[SingleJson] | SingleJson): A list of `SingleJson` objects representing
        the action definition files.

    Raises:
        requests.HTTPError:
        json.JSONDecodeError:

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.job_instance_id = job_instance_id
    response = api_client.get_installed_jobs()
    validate_response(response, validate_json=True)

    return response.json()


def get_connector_cards(
    chronicle_soar: ChronicleSOAR,
    integration_name: str | None = None,
    connector_identifier: str | None = None,
) -> list[ConnectorCard]:
    """Gets all the connector cards.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        integration_name (str | None): The integration name.
        connector_identifier (str | None): The connector identifier.

    Returns:
        list[ConnectorCard]: list of all connector cards.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.integration_name = integration_name
    api_client.params.connector_identifier = connector_identifier

    response = api_client.get_connector_cards()
    validate_response(response, validate_json=True)
    response_json = response.json()

    def to_card(card: ConnectorCard, integration_fallback: str | None) -> ConnectorCard:
        return ConnectorCard.from_json(
            connector_card_json={
                **card,
                "integration": card.get("integration") or integration_fallback,
            }
        )

    if isinstance(response_json, dict) and "connectorInstances" in response_json:
        return [to_card(card, integration_name) for card in response_json["connectorInstances"]]

    return [
        to_card(card, connector_card.get("integration") or integration_name)
        for connector_card in response_json
        for card in connector_card.get("cards", [])
    ]


def list_custom_fields(
    chronicle_soar,
    filter_: str | None = None,
) -> list[CustomField]:
    """List custom fields.

    Args:
        chronicle_soar: A chronicle soar SDK object
        filter_: Filter value for the search

    Returns:
        (list[CustomField]): The case details object

    Raises:
        requests.HTTPError: If failed to request or request status is not 200
        json.JSONDecoderError: If parsing the response fails

    """
    url = f"{get_sdk_api_uri(chronicle_soar)}/customFields"
    params = {}
    if filter_ is not None:
        params["$filter"] = filter_

    response = chronicle_soar.session.get(url=url, params=params)

    try:
        validate_response(response, validate_json=True)

    except InternalJSONDecoderError:
        return []

    return [CustomField.from_json(item) for item in response.json()["customFields"]]


def list_custom_field_values(
    chronicle_soar,
    parent: str,
) -> list[CustomFieldValue]:
    """Get custom field value for case or alert.

    Args:
        chronicle_soar: A chronicle soar SDK object
        parent: Parent path for custom field value, f. ex.: cases/1, cases/1/alerts/1

    Returns:
        (list[CustomFieldValue]): The case details object

    Raises:
        requests.HTTPError: If failed to request or request status is not 200
        json.JSONDecoderError: If parsing the response fails

    """
    url = f"{get_sdk_api_uri(chronicle_soar)}/{parent}/customFieldValues"
    response = chronicle_soar.session.get(url=url)

    try:
        validate_response(response, validate_json=True)

    except InternalJSONDecoderError:
        return []

    return [CustomFieldValue.from_json(item) for item in response.json()["customFieldValues"]]


def set_custom_field_values(
    chronicle_soar,
    parent: str,
    custom_field_id: int,
    values: [str],
) -> CustomFieldValue:
    """Set custom field values

    Args:
        chronicle_soar: A chronicle soar SDK object
        parent (str): parent path for custom field value i.e.: cases/1, cases/1/alerts/1
        custom_field_id (int): custom field id
        values ([str]): list of custom field values to set

    Returns:
        CustomFieldValue: CustomFieldValue object

    """
    url = f"{get_sdk_api_uri(chronicle_soar)}/{parent}/customFieldValues/{custom_field_id}"
    payload = {
        "values": values,
    }
    response = chronicle_soar.session.patch(url=url, json=payload)
    validate_response(response, validate_json=True)
    return CustomFieldValue.from_json(response.json())


def batch_set_custom_field_values(
    chronicle_soar,
    identifier: int,
    parent: str,
    custom_fields_values_mapping: dict[int, list[str]],
) -> list[CustomFieldValue]:
    """Batch set custom fields values

    Args:
        chronicle_soar: A chronicle soar SDK object
        identifier (int): parent identifier
        parent (str): parent path for custom field value i.e.: cases/1, cases/1/alerts/1
        custom_fields_values_mapping (dict[int: list[str]]): custom field ids to
            values mapping

    Returns:
        list[CustomFieldValue]: list of CustomFieldValue objects

    """
    url = f"{get_sdk_api_uri(chronicle_soar)}/{parent}/customFieldValues:batchUpdate"
    requests = []

    for custom_field_id, custom_field_values in custom_fields_values_mapping.items():
        requests.append(
            {
                "customFieldId": custom_field_id,
                "values": custom_field_values,
                "identifier": identifier,
            },
        )

    payload = {"requests": requests}
    response = chronicle_soar.session.post(url=url, json=payload)
    validate_response(response, validate_json=True)

    return [
        CustomFieldValue.from_json(custom_field_value)
        for custom_field_value in response.json().get("customFieldValues", [])
    ]


# ==== POST ==== #
def get_user_profile_cards(
    chronicle_soar: ChronicleSOAR,
    search_term: str = "",
    requested_page: int = 0,
    page_size: int = 20,
    filter_by_role: bool = False,
    filter_disabled_users: bool = False,
    filter_support_users: bool = False,
    fetch_only_support_users: bool = False,
    filter_permission_types: list[int] = None,
) -> SingleJson:
    """Retrieve user profile cards by page and filter.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        search_term (str): Search terms
        requested_page (int): Starting offset for returning a users' page
        page_size (int): Number of users to return
        filter_by_role (bool): Whether to filter out by role
        filter_disabled_users (bool): Whether to filter out disabled users
        filter_support_users (bool): Whether to filter out support users
        fetch_only_support_users (bool): Whether to return support users only.
        filter_permission_types (list[int] | None):
            List of filter permission types (e.g. 0)

    Examples:
        An example of the response JSON:
        {
            "objectsList": [
                {
                "firstName": "string",
                "lastName": "string",
                "userName": "string",
                "accountState": 0
                }
            ],
            "metadata": {
                "totalNumberOfPages": 0,
                "totalRecordsCount": 0,
                "pageSize": 0
            }
        }

    Returns:
        SingleJson: The response from SOAR server - the user profile card

    Raises:
        requests.HTTPError: If server returns a non-success status code
        json.JSONDecodeError: If the returned value is not a valid JSON

    """
    filter_permission_types = none_to_default_value(filter_permission_types, [])
    api_client = get_soar_client(chronicle_soar)

    api_client.params.search_term = search_term
    api_client.params.requested_page = requested_page
    api_client.params.page_size = page_size
    api_client.params.filter_by_role = filter_by_role
    api_client.params.filter_disabled_users = filter_disabled_users
    api_client.params.filter_support_users = filter_support_users
    api_client.params.fetch_only_support_users = fetch_only_support_users
    api_client.params.filter_permission_types = filter_permission_types
    response = api_client.get_users_profile_cards()
    validate_response(response)
    return response.json()


def get_alert_events(
    chronicle_soar: ChronicleSOAR,
    case_id: str | int,
    alert_identifier: str,
) -> list[AlertEvent]:
    """Get specific alert's events

    Args:
        chronicle_soar (ChronicleSOAR): _description_
        case_id (str | int): Case ID. Example: 13, "41"
        alert_identifier (str):
            The alert's identifier (='{alert.name}_{alert.id}'). Example:
            alert.name=SERVICE_ACCOUNT_USED
            alert.id=c3b80f09-38d3-4328-bddb-b938ccee0256
            identifier=SERVICE_ACCOUNT_USED_c3b80f09-38d3-4328-bddb-b938ccee0256

    Returns:
        list[SingleJson]: The request's response JSON. A list of events' JSONs

    Raises:
        requests.HTTPError: If server returns a non-success status code
        json.JSONDecodeError: If the returned value is not a valid JSON

    """
    endpoint = "api/external/v1/dynamic-cases/GetAlertEvents"
    url = urljoin(chronicle_soar.API_ROOT, endpoint)
    payload = {
        "caseId": case_id,
        "alertIdentifier": alert_identifier,
    }

    chronicle_soar.LOGGER.info(
        f"Calling endpoint {endpoint} to user profile cards",
    )
    response = chronicle_soar.session.post(url, json=payload)
    validate_response(response)

    return [AlertEvent.from_json(event) for event in response.json()]


def get_env_action_def_files(
    chronicle_soar: ChronicleSOAR,
) -> list[SingleJson]:
    """Retrieve a list of environment action definition files.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object

    Returns:
        (list[SingleJson]): A list of `SingleJson` objects representing
        the action definition files.

    Raises:
        requests.HTTPError:
        json.JSONDecodeError:

    """
    endpoint = "external/v1/settings/GetEnvironmentActionDefinitions"
    url = urljoin(chronicle_soar.API_ROOT, endpoint)
    payload = [chronicle_soar.environment]

    chronicle_soar.LOGGER.info(
        f"Calling endpoint {endpoint} to get all actions def files",
    )
    response = chronicle_soar.session.post(url, json=payload)
    validate_response(response, validate_json=True)

    return response.json()


def get_integration_full_details(
    chronicle_soar: ChronicleSOAR,
    integration_identifier: str,
) -> SingleJson:
    """Retrieves the full-details file of the integration.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        integration_identifier (str): The integration's ID (e.g. VirusTotalV3)


    Returns:
        (SingleJSON): The response JSON containing the full details of the integration.

    Raises:
        requests.HTTPError:
        json.JSONDecodeError:

    """
    # FIXME: Might not work on custom integrations
    api_client = get_soar_client(chronicle_soar)

    api_client.params.integration_identifier = integration_identifier

    response = api_client.get_integration_full_details()
    validate_response(response, validate_json=False)
    return response.json()


def get_integration_instance_details_by_id(
    chronicle_soar: ChronicleSOAR,
    integration_identifier: str,
    instance_id: str,
    environments: list[str] | None = None,
) -> SingleJson | None:
    """Retrieves the details of the integration instance by its id.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        integration_identifier (str): The integration's ID (e.g. VirusTotalV3)
        instance_id (str): The instance's ID
        environments (list[str] | None)): SOAR Environments list

    Returns:
        (SingleJSON | None): The response JSON containing the full details of the
            integration.

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.integration_identifier = integration_identifier
    api_client.params.instance_id = instance_id
    api_client.params.environments = environments or [DEFAULT_ENVIRONMENT]

    response = api_client.get_integration_instance_details_by_id()

    try:
        validate_response(response, validate_json=True)

    except InternalJSONDecoderError:
        return None

    return _get_instance_details(response.json(), instance_id)


def get_integration_instance_details_by_name(
    chronicle_soar: ChronicleSOAR,
    integration_identifier: str,
    instance_display_name: str,
    environments: list[str] | None = None,
) -> SingleJson | None:
    """Retrieves the details of the integration instance by its display name.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        integration_identifier (str): The integration's ID (e.g. VirusTotalV3)
        instance_display_name (str): The instance's display name

    Returns:
        (SingleJSON | None): The response JSON containing the full details of the
            integration.

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.integration_identifier = integration_identifier
    api_client.params.instance_display_name = instance_display_name
    api_client.params.environments = environments or [DEFAULT_ENVIRONMENT]

    response = api_client.get_integration_instance_details_by_name()

    try:
        validate_response(response, validate_json=True)

    except InternalJSONDecoderError:
        return None

    return _get_instance_details(response.json(), instance_display_name)


def _get_instance_details(
    instance_data: SingleJson | list[SingleJson],
    filter_key: str,
) -> SingleJson | None:
    """Get instance details by instance name or identifier."""
    if isinstance(instance_data, dict):
        if "integrationInstances" in instance_data:
            return instance_data["integrationInstances"][0]

        return instance_data

    for instance_detail in instance_data:
        instance_name = instance_detail.get("instanceName")
        identifier = instance_detail.get("identifier")

        if filter_key in [instance_name, identifier]:
            return instance_detail

    return None


def get_installed_integrations_of_environment(
    chronicle_soar: ChronicleSOAR,
    environment: str,
    integration_identifier: str = "-",
) -> list[InstalledIntegrationInstance]:
    """Fetch all integrations installed for provided environments.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        environment (str): instance environments list.
        integration_identifier (str | None): The integration identifier.

    Returns:
        list[InstalledIntegrationInstance]: A list of dictionary objects representing
        integration instances.

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.environment = environment
    api_client.params.integration_identifier = integration_identifier

    response = api_client.get_installed_integrations_of_environment()
    validate_response(response)
    instances = safe_json_for_204(response, default_for_204={"integrationInstances": []})
    instances = instances.get("instances", []) or instances.get("integrationInstances", [])
    return [InstalledIntegrationInstance.from_json(instance) for instance in instances]


def set_alert_priority(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_identifier: str,
    alert_name: str,
    priority: int,
) -> None:
    """Set alert priority.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        alert_identifier (str): Chronicle SOAR Alert Identifier
        alert_name (str): Chronicle SOAR Alert Name
        priority (int): Chronicle SOAR priority enum value

    Raises:
        requests.HTTPError:

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.alert_identifier = alert_identifier
    api_client.params.alert_name = alert_name
    api_client.params.priority = priority

    response = api_client.set_alert_priority()
    validate_response(response, validate_json=False)


def remove_case_tag(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    tag: str,
    alert_identifier: str | None = None,
) -> None:
    """Remove a case tag.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        alert_identifier (str): Chronicle SOAR Alert Identifier
        tag (str): A tag to remove

    Raises:
        requests.HTTPError:

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.tag = tag
    api_client.params.alert_identifier = alert_identifier
    response = api_client.remove_case_tag()
    validate_response(response, validate_json=False)


def get_entity_data(
    chronicle_soar: ChronicleSOAR,
    entity_identifier: str,
    entity_environment: str,
    entity_type: str | None = None,
    last_case_type: int = 0,
    case_distribution_type: int = 0,
) -> SingleJson:
    """Fetch entity data.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        entity_identifier (int): Entity identifier
        entity_environment (str): Entity environment
        entity_type (str): Entity type
        last_case_type: (int): Last case type
        case_distribution_type: (int): Case distribution type

    Raises:
        requests.HTTPError:

    Returns:
        dict: Entity

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.entity_identifier = entity_identifier
    api_client.params.entity_type = entity_type
    api_client.params.entity_environment = entity_environment
    api_client.params.last_case_type = last_case_type
    api_client.params.case_distribution_type = case_distribution_type

    response = api_client.get_entity_data()
    validate_response(response, validate_json=False)
    return response.json()


# ==== PATCH ==== #
def set_case_score_bulk(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    score: float,
) -> SingleJson:
    """Set case scores in bulk.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        score (float): Chronicle SOAR score

    Raises:
        requests.HTTPError:

    Returns:
        Response JSON, contains success status and lists of failed cases if any.
        {
            "isSuccessful": false,
            "invalidScoreCaseIds": [2],
            "notFoundCaseIds": null
        }

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.score = score
    response = api_client.set_case_score_bulk()
    validate_response(response, validate_json=False)
    return response.json()


def save_attachment_to_case_wall(
    chronicle_soar: ChronicleSOAR,
    attachment_data: CaseWallAttachment,
) -> SingleJson:
    """Save file directly to the case wall.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        attachment_data (CaseWallAttachment): ..data_models.CaseWallAttachment object.

    """
    api_client = get_soar_client(chronicle_soar)

    file_name_for_description = f"{attachment_data.name}{attachment_data.file_type}"
    final_description = (
        attachment_data.description or f'File "{file_name_for_description}" added to the case wall.'
    )
    api_client.params.case_id = attachment_data.case_id or chronicle_soar.case_id
    api_client.params.base64_blob = attachment_data.base64_blob
    api_client.params.name = attachment_data.name
    api_client.params.description = final_description
    api_client.params.file_type = attachment_data.file_type
    api_client.params.is_important = attachment_data.is_important

    response = api_client.save_attachment_to_case_wall()
    validate_response(response, validate_json=False)
    return response.json()


def get_full_case_details(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    case_type: str | None = None,
    *,
    case_expand: list[str] | None = None,
    alert_expand: list[str] | None = None,
) -> SingleJson:
    """Get full case details with explicit expand controls.

    Important:
    - No implicit expand.
    - Expand must be explicitly provided.

    Args:
        case_expand: Fields to expand on /cases endpoint.
        alert_expand: Fields to expand on /caseAlerts endpoint.

    """
    _validate_expand_parameters(case_expand=case_expand, alert_expand=alert_expand)
    api_client = get_soar_client(chronicle_soar)
    p = api_client.params

    p.case_id = case_id
    p.case_type = case_type
    p.case_expand = case_expand
    p.alert_expand = alert_expand

    response = api_client.get_full_case_details()
    validate_response(response, validate_json=False)

    results = response.json()

    if case_type == "alert" and isinstance(results, dict):
        alerts_data = results.pop("caseAlerts", results.pop("case_alerts", []))
        results["alerts"] = alerts_data

    return results


def get_case_insights(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
) -> SingleJson:
    """Get case attachments.

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    response = api_client.get_case_insights()
    validate_response(response)
    insights = safe_json_for_204(response, default_for_204={"activities": []})
    insights = insights.get("activities", insights.get("insights", []))

    return [Insight.from_json(insight).to_json() for insight in insights]


def get_federation_cases(
    chronicle_soar: ChronicleSOAR,
    continuation_token: str,
) -> SingleJson:
    """Get federation cases
    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        continuation_token (str): Continuation token.

    Returns:
        SingleJson: Response JSON.

    """
    fetch_parameters = {
        "continuationToken": continuation_token,
    }
    chronicle_soar.LOGGER.info(
        f"Fetch endpoint: {chronicle_soar.API_ROOT}, parameters: {fetch_parameters}"
    )
    api_client = get_soar_client(chronicle_soar)
    api_client.params.continuation_token = continuation_token
    response = api_client.get_federation_cases()
    validate_response(response, validate_json=False)
    return response


def get_workflow_instance_card(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_identifier: str,
) -> SingleJson:
    """Get workflow instance card

    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        alert_identifier (str): Chronicle SOAR Alert Identifier

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.alert_identifier = alert_identifier
    response = api_client.get_workflow_instance_card()
    validate_response(response, validate_json=False)
    return response.json()


# TODO: Divide this to some classes like Alert or Case related classes
def patch_federation_cases(
    chronicle_soar: ChronicleSOAR,
    cases_payload: SingleJson,
    api_root: str | None = None,
    api_key: str | None = None,
) -> SingleJson:
    """Patch federation cases
    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        cases_payload (SingleJson): Cases payload.
        api_root (str | None): API root.
        api_key (str | None): API key.

    Returns:
        SingleJson: Response JSON.

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.cases_payload = cases_payload
    if api_root:
        chronicle_soar.API_ROOT = api_root
    api_client.params.api_key = api_key
    response = api_client.patch_federation_cases()
    validate_response(response, validate_json=False)
    return response


def pause_alert_sla(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_identifier: str,
    message: str,
) -> SingleJson:
    """Pause alert sla
    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        alert_identifier (str): Chronicle SOAR Alert Identifier
        message (str): Chronicle SOAR message

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.alert_identifier = alert_identifier
    api_client.params.message = message
    response = api_client.pause_alert_sla()
    validate_response(response, validate_json=False)


def resume_alert_sla(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_identifier: str,
    message: str,
) -> SingleJson:
    """Resume alert sla
    Args:
        chronicle_soar (ChronicleSoar): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        alert_identifier (str): Chronicle SOAR Alert Identifier
        message (str): Chronicle SOAR message

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.alert_identifier = alert_identifier
    api_client.params.message = message
    response = api_client.resume_alert_sla()
    validate_response(response, validate_json=False)


def change_case_description(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    description: str,
) -> SingleJson:
    """Change case description
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        description (str): Chronicle SOAR case description

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.description = description

    response = api_client.change_case_description()
    validate_response(response, validate_json=False)
    return response.json()


def get_users_profile(
    chronicle_soar: ChronicleSOAR,
    display_name: str,
    search_term: str,
    filter_by_role: bool,
    requested_page: int,
    page_size: int,
    should_hide_disabled_users: bool,
) -> SingleJson:
    """Get users profile
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        display_name (str): Chronicle SOAR display name
        search_term (str): Chronicle SOAR search term
        filter_by_role (bool): Chronicle SOAR filter by role
        requested_page (int): Chronicle SOAR requested page
        page_size (int): Chronicle SOAR page size
        should_hide_disabled_users (bool): Chronicle SOAR should hide disabled users

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.search_term = search_term
    api_client.params.display_name = display_name
    api_client.params.filter_by_role = filter_by_role
    api_client.params.requested_page = requested_page
    api_client.params.page_size = page_size
    api_client.params.should_hide_disabled_users = should_hide_disabled_users

    response = api_client.get_users_profile()
    try:
        validate_response(response, validate_json=True)
    except InternalJSONDecoderError:
        return {}

    return response.json()


def get_investigator_data(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_identifier: str,
) -> SingleJson:
    """Get investigator data.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int): Chronicle SOAR case id.
        alert_identifier (str): Chronicle SOAR alert identifier.

    Returns:
        SingleJson: Response JSON.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.alert_identifier = alert_identifier
    response = api_client.get_investigator_data()
    validate_response(response, validate_json=True)
    return response.json()


def remove_entities_from_custom_list(
    chronicle_soar: ChronicleSOAR,
    list_entities_data: list[SingleJson] | None = None,
) -> SingleJson:
    """Remove entities from custom list"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.list_entities_data = list_entities_data

    response = api_client.remove_entities_from_custom_list()

    validate_response(response, validate_json=False)
    return response.json()


def add_entities_to_custom_list(
    chronicle_soar: ChronicleSOAR,
    identifier: str | None = None,
    category: str | None = None,
    environment: str | None = None,
) -> SingleJson:
    """Add entities to custom list"""
    api_client = get_soar_client(chronicle_soar)

    api_client.params.identifier = identifier
    api_client.params.category = category
    api_client.params.environment = environment

    response = api_client.add_entities_to_custom_list()
    validate_response(response, validate_json=False)
    return response.json()


def get_traking_list_record(
    chronicle_soar: ChronicleSOAR,
    category_name: str = "",
    entity_id: str = "",
) -> SingleJson:
    """Get traking list record"""
    api_client = get_soar_client(chronicle_soar)

    api_client.params.category_name = category_name
    api_client.params.entity_id = entity_id

    response = api_client.get_traking_list_record()

    return {"custom_lists": response if isinstance(response, list) else response.json()}


def get_traking_list_records_filtered(
    chronicle_soar: ChronicleSOAR,
    category_name: str = "",
    entity_id: str = "",
    environment: str | None = None,
) -> SingleJson:
    """Get traking list records filtered"""
    api_client = get_soar_client(chronicle_soar)

    api_client.params.category_name = category_name
    api_client.params.entity_id = entity_id
    api_client.params.environment = environment

    response = api_client.get_traking_list_records_filtered()

    return {"custom_lists": response if isinstance(response, list) else response.json()}


def execute_bulk_assign(
    chronicle_soar: ChronicleSOAR,
    case_ids: list[int],
    user_name: str,
) -> SingleJson:
    """Execute bulk assign"""
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_ids = case_ids
    api_client.params.user_name = user_name

    response = api_client.execute_bulk_assign()
    validate_response(response, validate_json=False)


def execute_bulk_close_case(
    chronicle_soar: ChronicleSOAR,
    case_ids: list[int],
    close_reason: str | None = None,
    root_cause: str | None = None,
    close_comment: str | None = None,
) -> SingleJson:
    """Execute bulk close case"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_ids = case_ids
    api_client.params.close_reason = close_reason
    api_client.params.root_cause = root_cause
    api_client.params.close_comment = close_comment

    response = api_client.execute_bulk_close_case()
    validate_response(response, validate_json=False)


def get_security_events(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
) -> list[SingleJson]:
    """Get security events.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int): Chronicle SOAR case id.

    Returns:
        list[SingleJson]: Response JSON.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.case_type = "alert"
    security_events = []
    if isinstance(api_client, LegacySoarApi):
        response = api_client.get_security_events()
        validate_response(response, validate_json=True)
        security_events.append(response)

    else:
        alerts_response = api_client.get_full_case_details()
        alert_ids = [alert["id"] for alert in alerts_response.json()["caseAlerts"]]
        for alert_id in alert_ids:
            api_client.params.alert_id = alert_id
            response = api_client.get_security_events()
            validate_response(response, validate_json=True)
            security_events.append(response)

    return _get_security_events_data(security_events)


def get_entity_cards(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
) -> list[EntityCard]:
    """Get entity cards.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int): Chronicle SOAR case id.

    Returns:
        list[SingleJson]: Response JSON.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    entity_cards = []

    response = api_client.get_entity_cards()
    validate_response(response, validate_json=True)
    entity_cards.append(response)

    return _get_entity_cards(entity_cards)


def _get_security_events_data(response_list: list[Response]) -> list[EventCard]:
    """Get security events data.

    Args:
        response_list (list[requests.Response]): Response list.

    Returns:
        list[SingleJson]: Response JSON.

    """
    security_events = []
    for response in response_list:
        response_data = response.json()
        if isinstance(response_data, list):
            security_events.extend(response_data)
        if isinstance(response_data, dict):
            for alert in response_data["alerts"]:
                security_events.extend(alert["security_event_cards"])

    return [EventCard.from_json(event) for event in security_events]


def _get_entity_cards(response_list: list[Response]) -> list[EventCard]:
    """Get security events data.

    Args:
        response_list (list[requests.Response]): Response list.

    Returns:
        list[SingleJson]: Response JSON.

    """
    entity_cards = []
    for response in response_list:
        response_data = response.json()

        for item in response_data.get("cards", []):
            entity_cards.append(item)
        for alert in response_data.get("alerts", []):
            entity_cards.extend(alert["entity_cards"])

    return [EntityCard.from_json(card) for card in entity_cards]


def rename_case(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    case_title: str,
) -> SingleJson:
    """Change case title
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        case_title (str): Chronicle SOAR case title

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.case_title = case_title

    response = api_client.rename_case()
    validate_response(response, validate_json=False)
    return response.json()


def add_comment_to_entity(
    chronicle_soar: ChronicleSOAR,
    content: str,
    entity_id: int = 0,
    author: str | None = None,
    entity_type: str | None = None,
    entity_identifier: str | None = None,
    entity_environment: str = DEFAULT_ENVIRONMENT,
) -> SingleJson:
    """Add comment to entity
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        entity_id (int): Entity ID
        content (str): Comment content
        author (str): Comment author
        entity_type (str): Entity type
        entity_identifier (str): Entity identifier
        entity_environment (str): Entity environment

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.entity_id = entity_id
    api_client.params.content = content
    api_client.params.author = author
    api_client.params.entity_type = entity_type
    api_client.params.entity_identifier = entity_identifier
    api_client.params.entity_environment = entity_environment

    response = api_client.add_comment_to_entity()
    validate_response(response, validate_json=False)


def assign_case_to_user(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    assign_to: str,
    alert_identifier: str | None = None,
) -> SingleJson:
    """Assign case to user
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        case_id (int): Chronicle SOAR case ID
        assign_to (str): Chronicle SOAR assign to
        alert_identifier (str): Chronicle SOAR Alert Identifier
    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.assign_to = assign_to
    api_client.params.alert_identifier = alert_identifier

    response = api_client.assign_case_to_user()
    try:
        validate_response(response, validate_json=True)
    except InternalJSONDecoderError:
        return []
    return response.json()


def get_email_template(
    chronicle_soar: ChronicleSOAR,
) -> EmailTemplate:
    """Get email template
    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object

    """
    api_client = get_soar_client(chronicle_soar)
    response = api_client.get_email_template()
    try:
        validate_response(response, validate_json=True)
    except InternalJSONDecoderError:
        return []
    response_data = response.json()
    if isinstance(response_data, list):
        return [EmailTemplate.from_json(res) for res in response_data]
    email_templates_list = response_data.get("emailTemplates", [])
    return [EmailTemplate.from_json(res) for res in email_templates_list]


def get_siemplify_user_details(
    chronicle_soar: ChronicleSOAR,
    search_term: str,
    filter_by_role: bool,
    requested_page: int,
    page_size: int,
    should_hide_disabled_users: str,
) -> UserDetails:
    """Get siemplify user details.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        search_term (str): Chronicle SOAR search term.
        filter_by_role (bool): Chronicle SOAR filter by role.
        requested_page (int): Chronicle SOAR requested page.
        page_size (int): Chronicle SOAR page size.
        should_hide_disabled_users (str): Chronicle SOAR should hide disabled users.

    Returns:
        UserDetails: A UserDetails object.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.search_term = search_term
    api_client.params.filter_by_role = filter_by_role
    api_client.params.requested_page = requested_page
    api_client.params.page_size = page_size
    api_client.params.should_hide_disabled_users = should_hide_disabled_users

    response = api_client.get_siemplify_user_details()
    validate_response(response, validate_json=True)
    return [
        UserDetails.from_json(res)
        for res in response.json().get("objectsList", response.json().get("legacySoarUsers", []))
    ]


def get_domain_alias(chronicle_soar: ChronicleSOAR, page_count: int = 0) -> SingleJson:
    """Get domain alias"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.page_count = page_count

    response = api_client.get_domain_alias()
    return response.json()


def add_tags_to_case_in_bulk(
    chronicle_soar: ChronicleSOAR,
    case_ids: list[int],
    tags: list[str],
) -> SingleJson:
    """Add tags to case in bulk"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_ids = case_ids
    api_client.params.tags = tags

    response = api_client.add_tags_to_case_in_bulk()
    try:
        validate_response(response, validate_json=True)
        return response.json()
    except InternalJSONDecoderError:
        return {}


def get_all_case_overview_details(
    chronicle_soar: ChronicleSOAR,
    case_id: int | str,
    *,
    case_expand: list[str] | None = None,
    alert_expand: list[str] | None = None,
    wall_expand: list[str] | None = None,
    entity_expand: list[str] | None = None,
) -> CaseDetails:
    """Get complete case overview using explicit expand parameters."""
    _validate_expand_parameters(
        case_expand=case_expand,
        alert_expand=alert_expand,
        wall_expand=wall_expand,
        entity_expand=entity_expand,
    )
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.case_expand = case_expand
    api_client.params.alert_expand = alert_expand
    api_client.params.wall_expand = wall_expand
    api_client.params.entity_expand = entity_expand

    response = api_client.get_all_case_overview_details()
    return CaseDetails.from_json(response)


def get_case_wall_records(
    chronicle_soar: ChronicleSOAR,
    case_id: int | str,
    *,
    wall_expand: list[str] | None = None,
) -> SingleJson:
    """Get case wall records.

    Expand behavior:
        - wall_expand is None → No expand query is sent.
        - wall_expand == ["*"] → Expand all fields.
        - wall_expand contains field names → Expand only those fields.
    """
    _validate_expand_parameters(wall_expand=wall_expand)
    api_client = get_soar_client(chronicle_soar)
    p = api_client.params

    p.case_id = case_id
    p.wall_expand = wall_expand

    response = api_client.get_case_wall_records()
    return response.json()


def get_entity_expand_cards(
    chronicle_soar: ChronicleSOAR,
    case_id: int | str,
    *,
    entity_expand: list[str] | None = None,
) -> SingleJson:
    """Get entity expand cards for a case.

    Expand behavior:
        - entity_expand is None → No expand query is sent.
        - entity_expand == ["*"] → Expand all fields.
        - entity_expand contains field names → Expand only those fields.
    """
    _validate_expand_parameters(entity_expand=entity_expand)
    api_client = get_soar_client(chronicle_soar)
    p = api_client.params

    p.case_id = case_id
    p.entity_expand = entity_expand

    response = api_client.get_entity_expand_cards()
    return response.json()


def get_attachments_metadata(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
) -> list[AttachmentMetadata]:
    """Get attachments metadata.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int): Chronicle SOAR case id.

    Returns:
        AttachmentMetadata: A list of AttachmentMetadata objects.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id

    response = api_client.get_attachments_metadata()
    validate_response(response)
    attachment_data = safe_json_for_204(
        response,
        default_for_204={"caseComments": []},
    )

    return [
        AttachmentMetadata.from_json(item)
        for item in attachment_data.get("caseComments", attachment_data.get("wall_data", []))
    ]


def add_attachment_to_case_wall(
    chronicle_soar: ChronicleSOAR,
    attachment: Attachment,
) -> str:
    """Add attachment to case wall.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        attachment (Attachment): Attachment data object.

    Returns:
        SingleJson: Response JSON.

    """
    api_client = get_soar_client(chronicle_soar)
    api_client.params.attachment = attachment

    response = api_client.add_attachment_to_case_wall()
    validate_response(response, validate_json=True)

    return response.json()


def create_entity(chronicle_soar: ChronicleSOAR, entity: CreateEntity) -> None:
    """Create entity using ExtendCaseGraph"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.entity_to_create = entity

    response = api_client.create_entity()
    validate_response(response, validate_json=False)


def import_simulator_custom_case(
    chronicle_soar: ChronicleSOAR,
    simulated_case_data: SingleJson,
) -> None:
    """Import Simulated Custom Case"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.simulated_case_data = simulated_case_data

    response = api_client.import_simulator_custom_case()
    validate_response(response, validate_json=False)


def add_or_update_case_task_v5(
    chronicle_soar: ChronicleSOAR,
    owner: str,
    title: str,
    content: str,
    due_date_unix_in_ms: int,
    case_id: str,
) -> None:
    """Import Simulated Custom Case"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.owner = owner
    api_client.params.title = title
    api_client.params.content = content
    api_client.params.due_date_unix_in_ms = due_date_unix_in_ms
    api_client.params.case_id = case_id

    response = api_client.add_or_update_case_task_v5()
    validate_response(response, validate_json=False)


def add_or_update_case_task_v6(
    chronicle_soar: ChronicleSOAR,
    owner: str,
    title: str,
    content: str,
    due_date_unix_in_ms: int,
    case_id: str,
) -> None:
    """Import Simulated Custom Case"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.owner = owner
    api_client.params.title = title
    api_client.params.content = content
    api_client.params.due_date_unix_in_ms = due_date_unix_in_ms
    api_client.params.case_id = case_id

    response = api_client.add_or_update_case_task_v6()
    validate_response(response, validate_json=False)


def attach_playbook_to_the_case(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    alert_group_identifier: str,
    alert_identifier: str,
    playbook_name: str,
    should_run_automatic: bool,
) -> None:
    """Attach playbook to the case."""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.alert_group_identifier = alert_group_identifier
    api_client.params.alert_identifier = alert_identifier
    api_client.params.playbook_name = playbook_name
    api_client.params.should_run_automatic = should_run_automatic

    response = api_client.attach_playbook_to_the_case()
    validate_response(response, validate_json=False)


def search_cases_by_everything(
    chronicle_soar: ChronicleSOAR,
    search_payload: SingleJson,
) -> SingleJson:
    """Import Simulated Custom Case"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.search_payload = search_payload

    response = api_client.search_cases_by_everything()
    validate_response(response, validate_json=True)

    return response.json()


def get_case_activities(
    chronicle_soar: ChronicleSOAR,
    case_id: int,
    query_params: dict[str, str] | None = None,
) -> SingleJson:
    """Get case activities with optional query parameters.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object.
        case_id (int): The case ID.
        query_params (dict[str, str] | None): Optional dictionary of query
            parameters for filtering, sorting, etc.
            Example: {"$filter": "activityType eq 'ManualComment'"}

    Returns:
        SingleJson: The response from the server, typically a dict with an
            "items" key.

    """
    api_client = get_soar_client(chronicle_soar)

    api_client.params.case_id = case_id
    api_client.params.query_params = query_params
    response = api_client.get_case_activities()
    try:
        validate_response(response, validate_json=True)
    except InternalJSONDecoderError:
        return {"items": []}

    result_data = response.json()
    if isinstance(result_data, list):
        return {"items": result_data}

    result_data["items"] = result_data.get("activities", [])

    return result_data


def get_cases_by_timestamp_filter(
    chronicle_soar: ChronicleSOAR,
    start_time: int,
    end_time: int,
    time_range_filter: int,
    environments: list[SingleJson],
    case_ids: list[int] | None = None,
) -> list[SingleJson]:
    """Get cases by timestamp filter"""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.start_time = start_time
    api_client.params.end_time = end_time
    api_client.params.time_range_filter = time_range_filter
    api_client.params.environment = environments
    api_client.params.case_ids = case_ids or []
    response = api_client.get_cases_by_timestamp_filter()
    return response
