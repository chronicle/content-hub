from __future__ import annotations

import dataclasses
import re
from collections import namedtuple
from enum import Enum
from typing import Any, Iterable

from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime

from TIPCommon.consts import DT_FORAMT_RFC3339, NUM_OF_MILLI_IN_SEC
from TIPCommon.smp_time import convert_string_to_unix_time
from TIPCommon.transformation import rename_dict_key
from TIPCommon.types import SingleJson
from scc_enterprise.core import GoogleSecurityCommandCenterConstants as GSCCConstants
from scc_enterprise.core import SCCEnterpriseConsts


CaseIterationSetup = namedtuple(
    "CaseIterationSetup",
    ["case_ids", "ticket_id_to_ticket_details", "ticket_id_to_ticket_comments"],
)

TicketIterationSetup = namedtuple(
    "CaseIterationSetup",
    ["ticket_id_to_case_id", "ticket_id_to_details", "ticket_id_to_comments"],
)

CaseIterationResult = namedtuple(
    "CaseIterationResult", ["closed_cases", "added_cases", "failed_cases"]
)

TicketIterationResult = namedtuple(
    "TicketIterationResult", ["closed_cases", "failed_cases"]
)


class DescriptionOutputType(Enum):
    HTML = SCCEnterpriseConsts.HTML_TEMPLATE_TYPE
    JWM = SCCEnterpriseConsts.JWM_TEMPLATE_TYPE


class CloudProviderEnum(Enum):
    AWS = "AMAZON_WEB_SERVICES"
    GCP = "GOOGLE_CLOUD_PLATFORM"
    AZURE = "MICROSOFT_AZURE"
    OTHER = SCCEnterpriseConsts.OTHER

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, CloudProviderEnum):
            return self.value == other.value

        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def keys(cls) -> list[str]:
        return ["GCP", "AWS", "AZURE"]

    @classmethod
    def get(cls, value: str) -> CloudProviderEnum:
        """This method is a safe retrieval for the cloudProvider enum.

        If the value is not available it will return a CloudProviderEnum OTHER
            object that can be used to retrieve name and value as 'OTHER'.

        Args:
            value (str): The value that needs to be extracted

        Returns:
            CloudProviderEnum
        """
        try:
            return cls(value)
        except ValueError:
            return CloudProviderEnum.OTHER


class SOARCaseDetailsForSCC:
    """SOAR case data that is saved to support SCC <-> ITSM sync jobs

    Attributes:
        name:
            The case name
            "organizations/123/sources/456/findings/123456/externalSystems/jira"
        assignees: The ticket assignee
        external_uid: Chronicle case uid
        status: Chronicle case status
        external_system_update_time: Chronicle case update time
        case_uri: Chronicle case url
        case_sla: Chronicle case SLA
        case_priority: Chronicle case priority
    """

    def __init__(
        self,
        assignees: str,
        external_uid: str,
        status: str,
        external_system_update_time: int,
        case_uri: str,
        case_priority: str,
        case_sla: int,
        name: str = "",
        sync_case: bool = True,
        **additional_keys,
    ) -> None:
        self.name = name
        self.assignees = assignees
        self.external_uid = external_uid
        self.status = status
        self.external_system_update_time = external_system_update_time
        self.case_uri = case_uri
        self.case_priority = case_priority
        self.case_sla = case_sla
        self.sync_case = sync_case
        self.additional_keys = additional_keys

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SOARCaseDetailsForSCC):
            return False

        return (
            self.name == other.name
            and self.assignees == other.assignees
            and self.external_uid == other.external_uid
            and self.status == other.status
            and self.case_uri == other.case_uri
            and self.case_priority == other.case_priority
            and self.case_sla == other.case_sla
            and self.sync_case == other.sync_case
            and self.additional_keys == other.additional_keys
        )

    def to_scc_json(self) -> SingleJson:
        case_sla = (
            int(self.case_sla)
            if self.case_sla and self.case_sla != SCCEnterpriseConsts.NOT_AVAILABLE
            else 0
        )

        return {
            "name": self.name,
            "assignees": self.assignees,
            "external_uid": self.external_uid,
            "status": self.status,
            "external_system_update_time": convert_unixtime_to_datetime(
                int(self.external_system_update_time or 0) * NUM_OF_MILLI_IN_SEC
            ).strftime(DT_FORAMT_RFC3339),
            "case_uri": self.case_uri,
            "case_sla": convert_unixtime_to_datetime(
                case_sla * NUM_OF_MILLI_IN_SEC
            ).strftime(DT_FORAMT_RFC3339),
            "case_priority": self.case_priority,
        }


class ITSMTicketDetailsForSCC:
    """ITSM ticket data that is saved to support SCC <-> ITSM sync jobs

    Attributes:
        id_: ITSM ticket id
        assignee: The ticket assignee
        description: ITSM ticket description
        uri: ITSM ticket url
        status: ITSM ticket status
        update_time: ITSM ticket update time
    """

    def __init__(
        self,
        id_: str,
        assignee: str,
        description: str,
        uri: str | None,
        status: str,
        update_time: int,
        **additional_keys,
    ) -> None:
        self.id_ = id_
        self.assignee = assignee
        self.description = description
        self.uri = uri
        self.status = status
        self.update_time = update_time
        self.additional_keys = additional_keys

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ITSMTicketDetailsForSCC):
            return False

        return (
            self.id_ == other.id_
            and self.assignee == other.assignee
            and self.description == other.description
            and self.uri == other.uri
            and self.status == other.status
            and self.additional_keys == other.additional_keys
        )

    def to_scc_json(self) -> SingleJson:
        return {
            "id": self.id_,
            "assignee": self.assignee,
            "uri": self.uri,
            "status": self.status,
            "update_time": convert_unixtime_to_datetime(
                int(self.update_time or 0) * NUM_OF_MILLI_IN_SEC
            ).strftime(DT_FORAMT_RFC3339),
        }


@dataclasses.dataclass
class ExternalSCCTicketInfo:
    """External data structure that is saved to support SCC <-> ITSM sync jobs

    This can be composed of SOARCaseDetailsForSCC and ITSMTicketDetailsForSCC.

    Attributes:
        case: A SOARCaseDetailsForSCC object
        ticket: A ITSMTicketDetailsForSCC

    Methods:
        from_json:
            A second constructor that builds the object from the SCC
            JSON context data
        to_json: Transform the object to the specific SCC JSON format
        update_by_case_details:
            Update the object's fields based on a SOARCaseDetailsForSCC object
        update_by_ticket_details:
            Update the object's fields based on an ITSMTicketDetailsForSCC
            object
    """

    case: SOARCaseDetailsForSCC
    ticket: ITSMTicketDetailsForSCC

    def __eq__(self, other) -> bool:
        if not isinstance(other, ExternalSCCTicketInfo):
            return False

        return self.case == other.case and self.ticket == other.ticket

    @classmethod
    def from_json(cls, scc_json: SingleJson) -> ExternalSCCTicketInfo:
        """Create an ExternalSCCTicketInfo object from an SCC external info JSON

        Args:
            scc_json: The JSON to build the object from

        Returns:
            A new ExternalSCCTicketInfo object
        """
        case_json = scc_json["case"]
        case = SOARCaseDetailsForSCC(**case_json)

        ticket_json = scc_json["ticket"]
        rename_dict_key(ticket_json, "id", "id_")
        ticket = ITSMTicketDetailsForSCC(**ticket_json)

        return cls(case, ticket)

    @classmethod
    def from_ext_sys_obj(
        cls, ext_sys_obj: "ChronicleSoarExternalSystems"
    ) -> ExternalSCCTicketInfo:
        """Create an ExternalSCCTicketInfo object from an SCC externalSystemInfo JSON
        object.

        Args:
            ext_sys_obj: The parsed external system object

        Returns:
            A new ExternalSCCTicketInfo object
        """

        case = SOARCaseDetailsForSCC(
            name=ext_sys_obj.name,
            assignees=ext_sys_obj.assignees,
            external_uid=ext_sys_obj.case_id,
            status=ext_sys_obj.status,
            external_system_update_time=(
                ext_sys_obj.external_system_update_time // NUM_OF_MILLI_IN_SEC
            ),
            case_uri=ext_sys_obj.case_uri,
            case_priority=ext_sys_obj.case_priority,
            case_sla=ext_sys_obj.case_sla // NUM_OF_MILLI_IN_SEC,
        )
        ticket = None

        if ext_sys_obj.ticket_info:
            ticket = ITSMTicketDetailsForSCC(
                id_=ext_sys_obj.ticket_info.id,
                assignee=ext_sys_obj.ticket_info.assignee,
                description=ext_sys_obj.ticket_info.description,
                uri=ext_sys_obj.ticket_info.uri,
                status=ext_sys_obj.ticket_info.status,
                update_time=ext_sys_obj.ticket_info.update_time // NUM_OF_MILLI_IN_SEC,
            )

        return cls(case, ticket)

    @classmethod
    def from_obj(cls, ext_scc_info: ExternalSCCTicketInfo) -> ExternalSCCTicketInfo:
        case_attrs = vars(ext_scc_info.case).copy()
        case_additional_keys = case_attrs.pop("additional_keys", {})

        ticket_attrs = vars(ext_scc_info.ticket).copy()
        ticket_additional_keys = ticket_attrs.pop("additional_keys", {})

        return cls(
            case=SOARCaseDetailsForSCC(**case_attrs, **case_additional_keys),
            ticket=ITSMTicketDetailsForSCC(**ticket_attrs, **ticket_additional_keys),
        )

    def update_by_case_details(self, soar_case_details: SOARCaseDetailsForSCC) -> None:
        """Update the object based on fields from a SOARCaseDetailsForSCC object

        Args:
            soar_case_details: The SOARCaseDetailsForSCC object
        """
        for attr in vars(self.case):
            new_val = getattr(soar_case_details, attr, None)
            if new_val is not None:
                setattr(self.case, attr, new_val)

    def update_by_ticket_details(
        self, itsm_ticket_details: ITSMTicketDetailsForSCC
    ) -> None:
        """Update the object based on fields from a ITSMTicketDetailsForSCC
            object

        Args:
            itsm_ticket_details: The ITSMTicketDetailsForSCC object
        """
        for attr in vars(self.ticket):
            if attr == "description":
                continue

            new_val = getattr(itsm_ticket_details, attr, None)
            if new_val is not None:
                setattr(self.ticket, attr, new_val)

    def to_full_json(self) -> SingleJson:
        """Return the object as a JSON format SCC expects

        Returns:
            The object as an SCC External Info JSON
        """
        full_json = {"case": dict(vars(self.case)), "ticket": dict(vars(self.ticket))}
        rename_dict_key(full_json["ticket"], "id_", "id")

        full_json["case"].pop("additional_keys", None)
        full_json["ticket"].pop("additional_keys", None)

        full_json["case"].update(**self.case.additional_keys)
        full_json["ticket"].update(**self.ticket.additional_keys)

        return full_json

    def to_context_json(self) -> SingleJson:
        scc_json = self.case.to_scc_json()
        scc_json["ticket_info"] = self.ticket.to_scc_json()

        return scc_json


@dataclasses.dataclass
class FindingContext:
    """Finding context data structure.

    Attributes:
        finding_id: A full name of an SCC finding -> name
        status: A state of SCC finding (ACTIVE / INACTIVE) -> state
        aps_score: APS Score calculated for the finding -> `attackExposure.score`

    Methods:
        build_from_finding_event_data:
            builds the object from the flat dict of a finding data (SOAR event data)
        to_json: Transform the object to the specific JSON format
        prepare_json_sorted:
            Takes an Iterable of FindingContext and prepares a sorted JSON for
            context value to be set with.
    """

    finding_id: str
    status: str
    aps_score: float
    resource_name: str
    project_display_name: str | None = None
    cloud_provider: CloudProviderEnum | None = None
    mute: str | None = None
    severity: str | None = None
    alert_identifier: str | None = None
    tc_count: int | None = None
    last_update_time: int | None = None

    def __post_init__(self) -> None:
        if self.aps_score is not None:
            self.aps_score = round(float(self.aps_score), 2)

        if isinstance(self.cloud_provider, str):
            self.cloud_provider = CloudProviderEnum(self.cloud_provider)

    @property
    def is_cloud_provider_aws(self) -> bool:
        return self.cloud_provider == CloudProviderEnum.AWS

    @property
    def is_cloud_provider_gcp(self) -> bool:
        return self.cloud_provider == CloudProviderEnum.GCP

    @property
    def is_active(self) -> bool:
        return self.status == GSCCConstants.STATE_MAPPING["Active"]

    @property
    def is_muted(self) -> bool:
        return self.mute == GSCCConstants.MUTED

    @classmethod
    def build_from_finding_event_data(
        cls, alert_identifier: str, finding_event_data: dict
    ) -> FindingContext:
        """
        Extracts fields to build a findings context data model.

        Args:
            alert_identifier: Chronicle SOAR Alert identifier
            finding_event_data:
                Flat dictionary that was built from the SCC findings data

        Returns:
            Findings context data model
        """
        project_display_name = finding_event_data.get("resource_projectDisplayName")
        if project_display_name is None:
            project_display_name = finding_event_data.get(
                "resource_gcpMetadata_projectDisplayName"
            )

        if (
            finding_event_data.get("findingClass")
            == GSCCConstants.TOXIC_COMBINATION_CLASS
        ):
            aps_score = finding_event_data.get("toxicCombination_attackExposureScore")
        else:
            aps_score = finding_event_data.get("attackExposure_score")
            aps_state = finding_event_data.get("attackExposure_state", "")
            if aps_score is None and aps_state.upper() == "CALCULATED":
                aps_score = 0

        tc_count = sum(
            (
                re.match(GSCCConstants.GROUP_MEMBERSHIPS_KEY, key) is not None
                and value == GSCCConstants.TOXIC_COMBINATION_GROUP
            )
            for key, value in finding_event_data.items()
        )

        event_time = (
            convert_string_to_unix_time(finding_event_data.get("eventTime"))
            if finding_event_data.get("eventTime")
            else 1
        )
        mute_update_time = (
            convert_string_to_unix_time(finding_event_data.get("muteUpdateTime"))
            if finding_event_data.get("muteUpdateTime")
            else 1
        )

        return cls(
            finding_id=finding_event_data.get("name"),
            status=finding_event_data.get("state"),
            mute=finding_event_data.get("mute"),
            severity=finding_event_data.get("severity"),
            resource_name=finding_event_data.get("resource_name"),
            project_display_name=project_display_name,
            alert_identifier=alert_identifier,
            aps_score=aps_score,
            tc_count=tc_count,
            last_update_time=max(event_time, mute_update_time),
        )

    @staticmethod
    def prepare_json_sorted(
        findings_context: Iterable[FindingContext],
    ) -> list[SingleJson]:
        """
        Prepares the JSON struct for context value.

        Args:
            findings_context: Iterable of FindingContext objs

        Returns:
            List of dicts sorted by state ASC and aps_score DESC
        """
        return [
            _finding_context.to_json()
            for _finding_context in sorted(
                findings_context,
                key=lambda _finding_context: (
                    _finding_context.state_sort_weight,
                    -GSCCConstants.SEVERITY_MAPPING.get(_finding_context.severity, -1),
                    # Additional sorting by ID just to ensure stable output from sorting
                    _finding_context.finding_id,
                ),
            )
        ]

    @property
    def state_sort_weight(self) -> int:
        # Not active -> bottom of the list
        if not self.is_active:
            return 2

        # Active but muted -> middle
        if self.is_muted:
            return 1

        # Active and NOT muted -> top of the list
        return 0

    def to_json(self) -> SingleJson:
        return {
            "finding_id": self.finding_id,
            "status": self.status,
            "mute": self.mute,
            "aps_score": self.aps_score,
            "severity": self.severity,
            "resource_name": self.resource_name,
            "project_display_name": self.project_display_name,
            "cloud_provider": self.cloud_provider.value,
            "alert_identifier": self.alert_identifier,
            "tc_count": self.tc_count,
            "last_update_time": self.last_update_time,
        }

    @property
    def name_without_location(self):
        return self.finding_id.replace("/locations/global", "")

    def __eq__(self, other: FindingContext) -> bool:
        return self.name_without_location == other.name_without_location

    def __hash__(self) -> int:
        return hash(self.name_without_location)


# Move to TIPCommon
@dataclasses.dataclass
class WorkflowInstance:
    status: int
    name: str
    definition_identifier: str
    original_workflow_definition_identifier: str
    run_count: int

    @classmethod
    def from_json(cls, workflow_instance_json: SingleJson) -> WorkflowInstance:
        """Parse workflow JSON into WorkflowInstance object."""
        return cls(
            status=workflow_instance_json["status"],
            name=workflow_instance_json["name"],
            definition_identifier=workflow_instance_json["definitionIdentifier"],
            original_workflow_definition_identifier=(
                workflow_instance_json["originalWorkflowDefinitionIdentifier"]
            ),
            run_count=workflow_instance_json["runCount"],
        )

    @property
    def is_running(self) -> bool:
        return self.status == SCCEnterpriseConsts.WF_STATUS_INPROGRESS
