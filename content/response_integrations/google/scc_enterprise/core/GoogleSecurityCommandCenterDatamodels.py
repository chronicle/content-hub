from __future__ import annotations

import re
import uuid
from typing import Any
import copy
import dataclasses

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.transformation import (
    add_prefix_to_dict,
    convert_list_to_comma_string,
    dict_to_flat,
)
from TIPCommon.types import SingleJson
from TIPCommon.validation import is_valid_email
from scc_enterprise.core.GoogleSecurityCommandCenterConstants import (
    DEFAULT_FALLBACK_SEVERITY,
    SEVERITY_MAPPING,
    VULNERABILITY_CLASS,
    URGENT_POSTURE_RULE_GENERATOR,
    URGENT_POSTURE_DEFAULT_DEVICE_PRODUCT,
    STATE_MAPPING,
    TOXIC_COMBINATION_CONFIG_KEY,
    MUTED,
    TOXIC_COMBINATION_GROUP,
    TOXIC_COMBINATION_CLASS,
)
from scc_enterprise.core.GoogleSecurityCommandCenterExceptions import GoogleSecurityCommandCenterException
from scc_enterprise.core.GoogleSecurityCommandCenterUtilsManager import (
    get_asset_resource_name,
    get_non_gcp_resource_name,
)
from scc_enterprise.core.SCCEnterpriseConsts import CLOUD_PROVIDER
from scc_enterprise.core.SCCEnterpriseDatamodels import CloudProviderEnum


FINDING_SOURCE_NAME_PATTERN = re.compile(r"organizations/\d+/sources/\d+")


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class FindingAlert(BaseModel):
    def __init__(self, raw_data, resource_data):
        super().__init__(raw_data)
        self._category = raw_data.get("category")
        self._name = raw_data.get("name")
        self._severity = raw_data.get("severity")

        self.id = self._name

        self.ticket_id = self._name
        self.display_id = f"GSCC_{self._name}"
        self.name = self._category
        self.description = raw_data.get("description")
        self.device_vendor = "Google Security Command Center"
        self.rule_generator = self._category
        self.source_grouping_identifier = self._category
        self.resource_data = dict(resource=resource_data)

        try:
            self.start_time = convert_string_to_unix_time(raw_data.get("eventTime"))
        except Exception:
            self.start_time = 1

        try:
            self.end_time = convert_string_to_unix_time(raw_data.get("eventTime"))
        except Exception:
            self.end_time = 1

    def as_event(self):
        event_data, resource_data = self.raw_data.copy(), self.resource_data.copy()
        event_data.update(resource_data)

        additional_key = {
            event_data["resource"]["type"]: resource_data["resource"].get(
                "displayName", ""
            )
        }
        event_data["resource"].update(additional_key)

        return dict_to_flat(event_data)

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        device_product_field,
        fallback_severity=DEFAULT_FALLBACK_SEVERITY,
    ):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.as_event())
        )
        alert_info.ticket_id = self.ticket_id
        alert_info.display_id = self.display_id
        alert_info.name = self.name
        alert_info.description = self.description
        alert_info.device_vendor = self.device_vendor
        alert_info.device_product = self.raw_data.get(
            device_product_field, "Google Security Command Center"
        )
        alert_info.priority = self.get_siemplify_severity(fallback_severity)
        alert_info.rule_generator = self.rule_generator
        alert_info.source_grouping_identifier = self.source_grouping_identifier
        alert_info.end_time, alert_info.start_time = self.end_time, self.start_time
        alert_info.events = [self.as_event()]

        return alert_info

    def get_siemplify_severity(self, fallback_severity):
        return SEVERITY_MAPPING.get(
            (
                fallback_severity.upper()
                if self._severity == "SEVERITY_UNSPECIFIED"
                else self._severity
            ),
            -1,
        )


class ExternalSystemsTicket(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        id_: str,
        assignee: str,
        description: str,
        uri: str,
        status: str,
        update_time: str,
    ):
        super().__init__(raw_data)
        self.id = id_
        self.assignee = assignee
        self.description = description
        self.uri = uri
        self.status = status
        self.update_time = (
            convert_string_to_unix_time(update_time) if update_time else 1
        )


class ChronicleSoarExternalSystems(BaseModel):
    def __init__(
        self,
        raw_data,
        name: str,
        assignees: str,
        case_id: str,
        status: str,
        external_system_update_time: str,
        case_uri: str,
        case_priority: str,
        case_sla: str,
        ticket_info: ExternalSystemsTicket | None,
    ):
        super().__init__(raw_data)
        self.name = name
        self.assignees = assignees
        self.case_id = case_id
        self.status = status
        self.external_system_update_time = (
            convert_string_to_unix_time(external_system_update_time)
            if external_system_update_time
            else 1
        )
        self.case_uri = case_uri
        self.case_priority = case_priority
        self.case_sla = convert_string_to_unix_time(case_sla) if case_sla else 1
        self.ticket_info = ticket_info


class AzureMetadata(BaseModel):
    def __init__(self, raw_data, subscription: dict = None, **_):
        super().__init__(raw_data)
        self.subscription_id = subscription.get("id") if subscription else None

    def get_project(self):
        return self.subscription_id


class AWSMetadata(BaseModel):
    def __init__(self, raw_data, account: dict = None, **_):
        super().__init__(raw_data)
        self.account_id = account.get("id") if account else None

    def get_project(self):
        return self.account_id


class GCPMetadata(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)
        self.project_display_name = kwargs.get("projectDisplayName")

    def get_project(self):
        return self.project_display_name


class Source(BaseModel):
    def __init__(self, raw_data: dict, name: str, display_name: str, description: str):
        super().__init__(raw_data)
        self.name = name
        self.display_name = display_name
        self.description = description


class Resource(BaseModel):
    def __init__(
        self,
        raw_data,
        cloud_provider: str,
        type_: str,
        display_name: str,
        project_display_name: str,
        cloud_metadata: dict,
        organization_id: str,
    ):
        super().__init__(raw_data)
        self.cloud_provider = CloudProviderEnum.get(cloud_provider)
        self.type = type_
        self.display_name = display_name
        self.project_display_name = project_display_name
        self.cloud_metadata = self.build_cloud_metadata(cloud_metadata)
        self.organization_id = organization_id

        self._asset_resource_name = None

    def build_cloud_metadata(
        self, cloud_metadata: dict
    ) -> AWSMetadata | AzureMetadata | GCPMetadata | None:
        """Build cloud metadata for a finding's resource object."""
        if self.is_aws:
            return AWSMetadata(cloud_metadata, **cloud_metadata)

        elif self.is_azure:
            return AzureMetadata(cloud_metadata, **cloud_metadata)

        elif self.is_gcp and cloud_metadata:
            return GCPMetadata(cloud_metadata, **cloud_metadata)

        return None

    @property
    def is_aws(self) -> bool:
        return self.cloud_provider == CloudProviderEnum.AWS

    @property
    def is_azure(self) -> bool:
        return self.cloud_provider == CloudProviderEnum.AZURE

    @property
    def is_gcp(self) -> bool:
        return self.cloud_provider == CloudProviderEnum.GCP

    def get_project(self) -> str | None:
        if self.cloud_metadata is not None:
            return self.cloud_metadata.get_project()

        return self.project_display_name

    @property
    def asset_resource_name(self):
        if self._asset_resource_name is not None:
            return self._asset_resource_name

        try:
            if self.is_aws or self.is_azure:
                self.raw_data["og_name"] = self.raw_data["name"]
                self._asset_resource_name = get_non_gcp_resource_name(
                    self.raw_data,
                    cloud_provider=self.cloud_provider,
                    organization_id=self.organization_id,
                )
            else:
                self._asset_resource_name = get_asset_resource_name(self.raw_data)
        except (GoogleSecurityCommandCenterException, KeyError):
            self._asset_resource_name = self.raw_data["name"]

        return self._asset_resource_name

    def to_json(self, logger=None):
        resource_data = self.raw_data.copy()
        try:
            resource_data["name"] = self.asset_resource_name
            resource_display_name = resource_data["displayName"]

            resource_data.update({resource_data["type"]: resource_display_name})

        except GoogleSecurityCommandCenterException as e:
            if logger is not None:
                logger.warn(str(e))

        except KeyError as e:
            if logger is not None:
                logger.warn(
                    f"Received a key error while adjusting resource data, "
                    f"missing key {e}"
                )

        return resource_data


class PostureFindingAlert(FindingAlert):
    def __init__(
        self,
        ack_id,
        raw_data: dict[str, Any],
        event_time: str,
        external_systems: ChronicleSoarExternalSystems,
        organization_id: str,
        cve_id: str,
        contacts: dict[str, Any],
        state: str,
        mute: str,
        mute_update_time: str,
        resource: Resource,
        effective_tags: list[dict[str, Any]],
        group_memberships: list[dict[str, str]],
        tc_related_findings: list[str] | None,
        aps_score: float,
        toxic_aps_score: float | None,
        finding_class: str,
        notification_config_name: str,
    ):
        super().__init__(raw_data, resource_data=resource.raw_data)

        self.ack_id = ack_id
        self.external_systems = external_systems
        self.rule_generator = URGENT_POSTURE_RULE_GENERATOR
        self.alert_id = self._name
        self.set_display_id(self.external_systems.case_id)
        self.event_time = convert_string_to_unix_time(event_time) if event_time else 1
        self.mute_update_time = (
            convert_string_to_unix_time(mute_update_time) if mute_update_time else 1
        )
        self.effective_tags = effective_tags
        self.organization_id = organization_id
        self.cve_id = cve_id
        self.contacts = contacts
        self.state = state
        self.mute = mute
        self.group_memberships = group_memberships
        self.tc_related_findings = tc_related_findings

        self.category = (
            self._category if self.cve_id is None else f"{self._category}_{self.cve_id}"
        )
        self.resource = resource
        self.finding_class = finding_class
        self.aps_score = toxic_aps_score if self.is_toxic_combination else aps_score
        self.notification_config_name = notification_config_name

    def set_display_id(self, case_id: str) -> None:
        self.display_id = f"GSCC_{self.name_without_location}_{case_id}"

    @property
    def severity(self):
        return self._severity

    @property
    def is_active(self):
        return self.state == STATE_MAPPING["Active"]

    @property
    def is_muted(self):
        return self.mute == MUTED

    @property
    def is_toxic_combination(self):
        return self.finding_class == TOXIC_COMBINATION_CLASS

    @property
    def from_tc_config(self):
        return TOXIC_COMBINATION_CONFIG_KEY in self.notification_config_name

    @property
    def tc_group_ids(self):
        return [
            membership.get("groupId")
            for membership in self.group_memberships
            if membership.get("groupType") == TOXIC_COMBINATION_GROUP
        ]

    @property
    def is_toxic_related_finding(self) -> bool:
        return bool(self.tc_group_ids) and not self.is_toxic_combination

    @property
    def source_name(self):
        source_name_match = FINDING_SOURCE_NAME_PATTERN.search(self._name)
        return source_name_match.group()

    @property
    def name_without_location(self):
        return self._name.replace("/locations/global", "")

    @property
    def last_update_time(self):
        return max(self.event_time, self.mute_update_time)

    def __hash__(self):
        return hash(self.display_id)

    def __eq__(self, other):
        return self.display_id == other.display_id

    def get_posture_alert_info(
        self,
        logger,
        alert_info: AlertInfo,
        environment_common,
        device_product_field,
        source_grouping_identifier_builder: SourceGroupingIdentifierBuilder,
        finding_owner_builder: FindingOwnerBuilder,
        fallback_severity=DEFAULT_FALLBACK_SEVERITY,
    ):

        finding_owner = finding_owner_builder.build_owner(
            logger=logger,
            tags=self.effective_tags,
            technical_contact=self.get_contact("technical"),
            security_contact=self.get_contact("security"),
        )

        source_grouping_identifier = (
            source_grouping_identifier_builder.build_source_grouping_identifier(
                logger=logger,
                cloud_provider=self.resource.cloud_provider,
                organization=self.organization_id,
                owner=finding_owner,
                finding_category=self.category,
                severity=self._severity,
                project=self.resource.get_project(),
                asset_type=self.resource.type,
            )
        )
        if self.is_toxic_combination:
            source_grouping_identifier += f"_{uuid.uuid4()}"

        event_data = self.as_event(logger)
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(event_data)
        )
        alert_info.ticket_id = self.ticket_id
        alert_info.display_id = self.display_id
        alert_info.name = self.category
        alert_info.description = self.description
        alert_info.device_vendor = self.device_vendor
        alert_info.device_product = self.raw_data.get(
            device_product_field, URGENT_POSTURE_DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity(fallback_severity)
        alert_info.rule_generator = f"SCC: {self.category}. Posture Findings"
        alert_info.source_grouping_identifier = source_grouping_identifier
        alert_info.end_time, alert_info.start_time = self.end_time, self.start_time
        alert_info.extensions = {
            "grouping_identifier": source_grouping_identifier,
            "owner": finding_owner,
        }
        alert_info.events = [event_data]
        alert_info.alert_update_supported = True
        alert_info.alert_metadata = self.alert_metadata

        return alert_info

    @property
    def alert_metadata(self) -> SingleJson:
        """ETL SOAR Alert Metadata fields.

        Supported keys: RelatedIds, RelationId
        """
        if self.is_toxic_combination and self.tc_related_findings is not None:
            return {"RelatedIds": self.tc_related_findings}

        if self.is_toxic_related_finding:
            return {"RelationId": self._name}

        return {}

    def as_event(self, logger=None):
        event_data = self.raw_data.copy()
        related_findings = event_data.get("toxicCombination", {}).get("relatedFindings")
        if related_findings:
            event_data["toxicCombination"]["relatedFindingsCSV"] = (
                convert_list_to_comma_string(related_findings)
            )
        resource_data = self.resource.to_json(logger)
        event_data.update({"resource": resource_data})

        for tag_dict in self.effective_tags:
            tag_key = tag_dict["tagKey"]
            tag_value = tag_dict["tagValue"].replace(f"{tag_key}/", "")
            tag_data = {f"effectiveTags_{tag_key}": tag_value}
            event_data.update(tag_data)

        return dict_to_flat(event_data)

    def get_contact(self, contact_type):
        contacts = self.contacts.get(contact_type, {}).get("contacts", [])
        if not contacts:
            return
        return contacts[0].get("email")


class FindingDetails(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        name: str,
        category: str,
        state: str,
        severity: str,
        finding_class: str,
        description: str,
        event_time: str,
        cve_id: str,
        recommendation: str,
        resource_name: str,
        resource_data: dict,
        external_systems: ChronicleSoarExternalSystems,
        aps_score: float,
        mute: str,
    ):
        super(FindingDetails, self).__init__(raw_data)
        self.name = name
        self.category = category
        self.state = state
        self.mute = mute
        self.severity = severity
        self.finding_class = finding_class
        self.description = description
        self.event_time = event_time
        self.cve_id = cve_id
        self.recommendation = recommendation
        self.resource_name = resource_name
        self.resource_data = resource_data
        self.external_systems = external_systems
        self.aps_score = aps_score
        self._asset_resource_name = None

    @property
    def name_without_location(self):
        return self.name.replace("/locations/global", "")

    @property
    def is_active(self):
        return self.state == STATE_MAPPING["Active"]

    @property
    def is_muted(self):
        return self.mute == MUTED

    @property
    def asset_resource_name(self):
        if self._asset_resource_name is not None:
            return self._asset_resource_name

        try:
            if self.resource_data is None:
                raise KeyError("Resource data is not enriched.")

            self._asset_resource_name = get_asset_resource_name(self.resource_data)
        except (GoogleSecurityCommandCenterException, KeyError):
            self._asset_resource_name = self.resource_name

        return self._asset_resource_name

    def get_asset_display_name(self):
        return self.raw_data.get("resource", {}).get(
            "display_name"
        ) or self.raw_data.get("resource", {}).get("displayName")

    def get_severity(self):
        return SEVERITY_MAPPING.get(self.severity, -1)

    def as_json(self):
        json_data = copy.deepcopy(self.raw_data)
        json_data["finding_name"] = self.name
        return json_data

    def to_table(self):
        return dict_to_flat(
            {
                "Category": self.category,
                "State": self.state,
                "Severity": self.severity,
                "Type": self.finding_class,
            }
        )

    def as_vulnerability_json(self):
        return self.raw_data.get("finding", {})

    def to_vulnerability_table(self):
        if self.finding_class == VULNERABILITY_CLASS:
            return dict_to_flat(
                {
                    "Category": self.category,
                    "Description": self.description,
                    "Severity": self.severity,
                    "Event Time": self.event_time,
                    "CVE": self.cve_id,
                }
            )

        return dict_to_flat(
            {
                "Category": self.category,
                "Description": self.description,
                "Severity": self.severity,
                "Event Time": self.event_time,
                "Recommendation": self.recommendation,
            }
        )


@dataclasses.dataclass(frozen=True)
class NotificationsConfig:
    raw_data: dict
    name: str
    config_id: str
    pubsub_topic: str
    service_account: str
    streaming_config: dict


@dataclasses.dataclass(frozen=True)
class SCCFilter:
    filter_name: str
    filter_value: list[str]
    operator: str = "="
    inverted: bool = False

    @property
    def is_empty(self) -> bool:
        return not self.filter_value

    def build_filter(self):
        filter_iterable = (
            f'{self.filter_name}{self.operator}"{value}"' for value in self.filter_value
        )
        filter_expression_base = "NOT " if self.inverted else ""

        return f'{filter_expression_base}({" OR ".join(filter_iterable)})'


@dataclasses.dataclass(frozen=True)
class SCCCombinedFilter:
    filter_value: list[SCCFilter | SCCCombinedFilter]
    use_or_operator: bool = True

    @property
    def is_empty(self) -> bool:
        return all(filter_.is_empty for filter_ in self.filter_value)

    def build_filter(self):
        operator = " OR " if self.use_or_operator else " AND "
        filters_generator = (
            f.build_filter() for f in self.filter_value if not f.is_empty
        )
        return f"({operator.join(filters_generator)})"


@dataclasses.dataclass(frozen=True)
class SCCFilterBuilder:
    severity: SCCFilter
    sources: SCCFilter
    cloud_filter: SCCCombinedFilter
    asset_type: SCCFilter
    category: SCCFilter
    external_systems: SCCCombinedFilter
    state: SCCFilter = SCCFilter(filter_name="state", filter_value=["ACTIVE"])
    mute: SCCFilter = SCCFilter(
        filter_name="mute", filter_value=["MUTED"], inverted=True
    )
    findings_class: SCCFilter = SCCFilter(
        filter_name="findingClass", filter_value=["MISCONFIGURATION", "VULNERABILITY"]
    )

    def build_filters(self):
        filters = (
            getattr(self, field.name).build_filter()
            for field in dataclasses.fields(self)
            if not getattr(self, field.name).is_empty
        )
        return " AND ".join(filters)


@dataclasses.dataclass(frozen=True)
class FindingOwnerBuilder:
    fallback_owner: str
    owner_tag_name: str | None

    def build_owner(
        self,
        logger,
        tags: list[dict[str, Any]],
        technical_contact: str,
        security_contact: str,
    ):
        """Build Owner for Findings based on builder settings.

        Args:
            logger: Logger to log errors if any
            tags: List of dicts with cloud tags
            technical_contact: Tech contact
            security_contact: Sec contact

        Returns:
             Finding owner
        """
        if self.owner_tag_name:
            tag_dict = next(
                filter(lambda tag: tag["tagKey"] == self.owner_tag_name, tags), None
            )
            if tag_dict is not None:
                tag_value = tag_dict["tagValue"].replace(f"{tag_dict['tagKey']}/", "")
                if is_valid_email(tag_value):
                    return tag_value

                logger.warn(
                    f"Tag value {tag_value} is not a valid email "
                    f"address, falling back to next in chain ..."
                )

        if technical_contact:
            if is_valid_email(technical_contact):
                return technical_contact

            logger.warn(
                f"Technical contact {technical_contact} is not a valid email "
                f"address, falling back to next in chain ..."
            )
        elif security_contact:
            if is_valid_email(security_contact):
                return security_contact

            logger.warn(
                f"Security contact value {security_contact} is not a valid email "
                f"address, falling back to next in chain ..."
            )
        return self.fallback_owner


@dataclasses.dataclass(frozen=True)
class SourceGroupingIdentifierBuilder:
    group_by_project: bool
    group_by_aws_account: bool
    group_by_azure_subscription: bool
    group_by_severity: bool
    group_by_asset_type: bool

    def add_project_and_asset_type(
        self,
        logger,
        source_grouping_identifier: str,
        cloud_provider: CloudProviderEnum,
        project: str,
        asset_type: str,
    ) -> str:
        """Add project and asset_type details with correct prefix based on Cloud Provider.

        Args:
            logger: Logger to log errors if any
            source_grouping_identifier: Source Grouping ID string
            cloud_provider: Cloud Provider Enum
            project: Project ID
            asset_type: Asset type

        Returns:
            New source grouping identifier
        """
        if self.group_by_project and cloud_provider == CloudProviderEnum.GCP:
            if project is None:
                logger.error(
                    "Unable to get findings project, falling back to NO_PROJECT"
                )
                project = "NO_PROJECT"
            source_grouping_identifier += f"_{cloud_provider.name}_PROJECT:{project}"

        elif self.group_by_aws_account and cloud_provider == CloudProviderEnum.AWS:
            if project is None:
                logger.error(
                    "Unable to get findings account, falling back to NO_ACCOUNT"
                )
                project = "NO_ACCOUNT"
            source_grouping_identifier += f"_{cloud_provider.name}_ACCOUNT:{project}"

        elif (
            self.group_by_azure_subscription
            and cloud_provider == CloudProviderEnum.AZURE
        ):
            if project is None:
                logger.error(
                    "Unable to get findings account, falling back to NO_SUBSCRIPTION"
                )
                project = "NO_SUBSCRIPTION"
            source_grouping_identifier += (
                f"_{cloud_provider.name}_SUBSCRIPTION:{project}"
            )

        if self.group_by_asset_type:
            if asset_type is None:
                logger.error(
                    "Unable to get findings asset type, "
                    "falling back to NO_ASSET_TYPE"
                )
                asset_type = "NO_ASSET_TYPE"
            source_grouping_identifier += (
                f"_{cloud_provider.name}_ASSET_TYPE:{asset_type}"
            )

        return source_grouping_identifier

    def build_source_grouping_identifier(
        self,
        logger,
        cloud_provider: CloudProviderEnum,
        organization: str,
        owner: str,
        finding_category: str,
        severity: str,
        project: str | None,
        asset_type: str | None,
    ):
        """Build Source Grouping Identifier based on builder settings.

        Args:
            logger: Logger to log errors if any
            cloud_provider: Cloud Provider Enum
            organization: Organization value
            owner: Owner value
            finding_category: Finding category
            severity: Finding severity converted to SOAR
            project: GCP Project or AWS Account from resource
            asset_type: GCP or AWS Asset type extracted from resource

        Returns:
            Source Grouping Identifier
        """
        cloud_provider_ = CLOUD_PROVIDER.format(cloud_provider.name)
        source_grouping_identifier = (
            f"{cloud_provider_}_"
            f"ORGANIZATION:{organization}_"
            f"OWNER:{owner}_"
            f"FINDING_CATEGORY:{finding_category}"
        )

        if self.group_by_severity:
            source_grouping_identifier += f"_SEVERITY:{severity}"

        source_grouping_identifier = self.add_project_and_asset_type(
            logger=logger,
            source_grouping_identifier=source_grouping_identifier,
            cloud_provider=cloud_provider,
            project=project,
            asset_type=asset_type,
        )

        return source_grouping_identifier
