from __future__ import annotations

import base64
import dataclasses
import json
import mimetypes
import os.path

from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
    CaseFilterStatusEnum,
)
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.base.job import Job
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.extraction import extract_job_param
from TIPCommon.rest.soar_api import (
    get_case_attachments,
    get_case_overview_details,
    save_attachment_to_case_wall,
)
from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.validation import ParameterValidator

from ..core.constants import (
    AFFECTED_CIS_CONTEXT_VALUE_CHUNK_SIZE,
    AFFECTED_CIS_KEY,
    AFFECTED_CIS_MAPPING_KEY,
    AFFECTED_CIS_REQUEST_LIMIT,
    CASE_ATTACHMENT_TYPE,
    FIELDS_TO_EXCLUDE,
    INCIDENT_NUMBERS_MAPPING_KEY,
    INCIDENTS_CONTEXT_VALUE_CHUNK_SIZE,
    INCIDENTS_KEY,
    INCIDENTS_REQUEST_LIMIT,
    INCIDENTS_SYNC_TAG,
    PROCESSED_CASES_TIMESTAMP_KEY,
    RELATED_OBJECTS_CONTEXT_VALUE_CHUNK_SIZE,
    RELATED_OBJECTS_KEY,
    RELATED_OBJECTS_MAPPING_KEY,
    SIEM_ATTACHMENT_PREFIX,
    SIEM_COMMENT_PREFIX,
    SNOW_ATTACHMENT_PREFIX,
    SNOW_COMMENT_PREFIX,
    SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
    SYNC_INCIDENTS_JOB_NAME,
    SYNC_LEVEL,
    TICKET_ID_CONTEXT_KEY,
)
from ..core.exceptions import (
    ServiceNowException,
    ServiceNowNotFoundException,
    ServiceNowRecordNotFoundException,
)
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from ..core.UtilsManager import (
    compare_nested_dicts,
    format_text,
    get_chunks_as_job_context_property,
    set_chunks_as_job_context_property,
    split_dict_into_chunks,
)

DEFAULT_HOURS_BACKWARDS = 0
PROCESSED_CASES_LIMIT = 100


@dataclasses.dataclass(slots=True, frozen=True)
class ServiceNowAuthParams:
    api_root: str
    username: str
    password: str
    verify_ssl: bool

    @classmethod
    def build_from_job(cls, chronicle_soar: SiemplifyJob) -> ServiceNowAuthParams:
        """Build integration auth params from SOAR job object."""
        return cls(
            api_root=extract_job_param(
                chronicle_soar,
                param_name="API Root",
                is_mandatory=True,
            ),
            username=extract_job_param(
                chronicle_soar,
                param_name="Username",
            ),
            password=extract_job_param(
                chronicle_soar,
                param_name="Password",
                remove_whitespaces=False,
            ),
            verify_ssl=extract_job_param(
                chronicle_soar,
                param_name="Verify SSL",
                is_mandatory=True,
                input_type=bool,
                default_value=True,
            ),
        )


class SyncIncidentsJob(Job):
    def __init__(self, script_name) -> None:
        super().__init__(script_name)
        self._cached_incident_numbers_mapping: dict[str, [int]] = {}
        self._cached_incident_numbers_reverse_mapping: dict[int, [str]] = {}
        self._cached_incidents_data: dict[str, dict] = {}
        self._incident_numbers_mapping: dict[str, [int]] = {}
        self._incidents_data: dict[str, dict] = {}
        self._updated_incidents_data: dict[str, dict] = {}
        self._incidents_changes: dict[str, dict[str, tuple]] = {}
        self._cached_related_objects_mapping: dict[str, dict] = {}
        self._cached_related_objects: dict[str, dict] = {}
        self._related_objects_mapping: dict[str, dict] = {}
        self._related_objects: dict[str, dict] = {}
        self._updated_related_objects_data: dict[str, dict] = {}
        self._related_objects_changes: dict[str, dict[str, tuple]] = {}
        self._cached_affected_cis_mapping: dict[str, dict] = {}
        self._cached_affected_cis: dict[str, dict] = {}
        self._affected_cis_mapping: dict[str, dict] = {}
        self._affected_cis: dict[str, dict] = {}
        self._updated_affected_cis: dict[str, dict] = {}
        self._affected_cis_changes: dict[str, dict[str, tuple]] = {}
        self._updated_incident_affected_cis: dict[str, [tuple]] = {
            "added": [],
            "removed": [],
        }
        self._processed_case_ids_mapping: dict[int, int] = {}

    def get_cache_data(self):
        """Get data from cache"""
        # Incidents
        self.logger.info("Getting cached incident numbers mapping from Job context")
        self._cached_incident_numbers_mapping = json.loads(
            self.soar_job.get_job_context_property(
                identifier=self.name_id, property_key=INCIDENT_NUMBERS_MAPPING_KEY
            )
            or "{}"
        )

        for incident_number, case_ids in self._cached_incident_numbers_mapping.items():
            for case_id in case_ids:
                self._cached_incident_numbers_reverse_mapping.setdefault(case_id, []).append(
                    incident_number
                )
        self.logger.info("Fetched cached incident numbers mapping from Job context")

        self.logger.info("Getting cached incidents data from Job context")
        self._cached_incidents_data = get_chunks_as_job_context_property(
            self.soar_job, self.name_id, INCIDENTS_KEY
        )
        self.logger.info(
            f"Fetched {len(self._cached_incidents_data)} cached incidents data from Job context"
        )

        # Related Objects
        self.logger.info("Getting cached related objects mapping from Job context")
        self._cached_related_objects_mapping = json.loads(
            self.soar_job.get_job_context_property(
                identifier=self.name_id, property_key=RELATED_OBJECTS_MAPPING_KEY
            )
            or "{}"
        )
        self.logger.info("Fetched cached related objects mapping from Job context")

        self.logger.info("Getting cached related objects data from Job context")
        self._cached_related_objects = get_chunks_as_job_context_property(
            self.soar_job, self.name_id, RELATED_OBJECTS_KEY
        )
        self.logger.info(
            f"Fetched {len(self._cached_related_objects)} cached related objects "
            f"data from Job context"
        )

        # Affected CIs
        self.logger.info("Getting cached affected CIs mapping from Job context")
        self._cached_affected_cis_mapping = json.loads(
            self.soar_job.get_job_context_property(
                identifier=self.name_id, property_key=AFFECTED_CIS_MAPPING_KEY
            )
            or "{}"
        )
        self.logger.info("Fetched cached affected CIs mapping from Job context")

        self.logger.info("Getting cached affected CIs data from Job context")
        self._cached_affected_cis = get_chunks_as_job_context_property(
            self.soar_job, self.name_id, AFFECTED_CIS_KEY
        )
        self.logger.info(
            f"Fetched {len(self._cached_affected_cis)} cached affected CIs from Job context"
        )

    def cleanup_cached_incident_numbers_mapping(
        self, case_id: int, new_incident_numbers: [str]
    ) -> None:
        """Clean up cached incident numbers mapping by removing case_id from the mapping

        Args:
            case_id (int): case id
            new_incident_numbers ([str]): new incident numbers associated with the case
        """
        additional_incident_numbers = list(
            set(self._cached_incident_numbers_reverse_mapping.get(case_id) or [])
            - set(new_incident_numbers)
        )

        if additional_incident_numbers:
            for incident_number in additional_incident_numbers:
                self._cached_incident_numbers_mapping[incident_number] = list(
                    set(self._cached_incident_numbers_mapping.get(incident_number, [])) - {case_id}
                )

                if self._cached_incident_numbers_mapping.get(incident_number) == []:
                    del self._cached_incident_numbers_mapping[incident_number]

    def get_case_ids(self, timestamp):
        """Get case ids from soar based on provided filters

        Args:
            timestamp (int): timestamp filter

        Returns:
            [int]: list of case ids
        """
        # Getting all cases from timestamp that have tag INCIDENTS_SYNC_TAG
        case_ids = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.OPEN,
            update_time_from_unix_time_in_ms=timestamp,
            start_time_from_unix_time_in_ms=timestamp,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
            max_results=PROCESSED_CASES_LIMIT,
            tags=[INCIDENTS_SYNC_TAG],
        )

        self.logger.info(f"Fetched {len(case_ids)} cases from SOAR to process")

        return case_ids

    def set_incident_numbers_mapping(self, case_id: int, incident_numbers: [str]) -> None:
        """Set incident numbers mapping

        Args:
            case_id (int): case id
            incident_numbers ([str]): list of incident numbers
        """
        if set(self._cached_incident_numbers_reverse_mapping.get(case_id) or []) != set(
            incident_numbers
        ):
            self.cleanup_cached_incident_numbers_mapping(case_id, incident_numbers)

            for incident_number in incident_numbers:
                self._incident_numbers_mapping[incident_number] = list(
                    set(
                        self._cached_incident_numbers_mapping.get(incident_number, [])
                        + self._incident_numbers_mapping.get(incident_number, [])
                        + [case_id]
                    )
                )

    def get_incident_numbers_mapping(self, timestamp):
        """Get incident numbers to case ids mapping

        Args:
            timestamp (int): timestamp filter
        """
        cases = [
            get_case_overview_details(self._soar_job, case_id)
            for case_id in self.get_case_ids(timestamp)
        ]

        for case in cases:
            ticket_ids = []

            if self.params.sync_level == SYNC_LEVEL.get("ALERT"):
                # getting incident numbers from alerts TICKET_ID_CONTEXT_KEY context key
                for alert in case.alerts:
                    ticket_ids.extend(
                        convert_comma_separated_to_list(
                            self._soar_job.get_context_property(
                                context_type=2,
                                identifier=alert.alert_group_identifier,
                                property_key=TICKET_ID_CONTEXT_KEY,
                            )
                            or []
                        )
                    )
            else:
                # getting incident numbers from cases TICKET_ID_CONTEXT_KEY context key
                ticket_ids.extend(
                    convert_comma_separated_to_list(
                        self._get_case_context_property(
                            case_id=str(case.id_), property_key=TICKET_ID_CONTEXT_KEY
                        )
                        or []
                    )
                )

            self.set_incident_numbers_mapping(case.id_, list(set(ticket_ids)))
            self._processed_case_ids_mapping[case.id_] = (
                case.modification_time_unix_time_ms or case.creation_time_unix_time_ms
            )

        self.logger.info("Fetched incident numbers mapping from SOAR")

    def get_incidents(self, incident_numbers, datetime=None):
        """Get incidents

        Args:
            incident_numbers ([str]): list of incident numbers
            datetime (datetime): datetime filter

        Returns:
            [Incident]: list of Incident objects
        """
        incidents = []
        sn_format_timestamp = (
            self.api_client.convert_datetime_to_sn_format(datetime) if datetime else None
        )

        if incident_numbers:
            for split_incident_numbers in [
                incident_numbers[i : i + INCIDENTS_REQUEST_LIMIT]
                for i in range(0, len(incident_numbers), INCIDENTS_REQUEST_LIMIT)
            ]:
                try:
                    incidents.extend(
                        self.api_client.get_incidents(
                            table_name=DEFAULT_TABLE,
                            numbers=split_incident_numbers,
                            created_on=sn_format_timestamp,
                            updated_on=sn_format_timestamp,
                            display_value=True,
                        )
                    )
                except ServiceNowRecordNotFoundException:
                    self.logger.info("Incidents not found")
        else:
            try:
                incidents.extend(
                    self.api_client.get_incidents(
                        table_name=DEFAULT_TABLE,
                        numbers=incident_numbers,
                        created_on=sn_format_timestamp,
                        updated_on=sn_format_timestamp,
                        display_value=True,
                    )
                )
            except ServiceNowRecordNotFoundException:
                self.logger.info("Incidents not found")

        return incidents

    def get_incident_related_objects_mapping(self, incident_data):
        """Get incident related objects to incident numbers mapping

        Args:
            incident_data (dict): raw incident data
        """
        for key, value in incident_data.items():
            if isinstance(value, dict) and value.get("link"):
                self._related_objects_mapping[value.get("link")] = {
                    "incident_numbers": list(
                        set(
                            self._cached_related_objects_mapping.get(value.get("link"), {}).get(
                                "incident_numbers", []
                            )
                            + self._related_objects_mapping.get(value.get("link"), {}).get(
                                "incident_numbers", []
                            )
                            + [incident_data.get("number")]
                        )
                    ),
                    "value": value.get("display_value"),
                    "key": key,
                }

    def get_incident_affected_cis_mapping(self):
        """Get incident affected CIs to incident numbers and sys_ids mapping"""
        affected_cis = []
        incident_sys_ids_mapping = {
            incident_data.get("sys_id"): incident_data.get("number")
            for incident_data in {
                **self._incidents_data,
                **self._cached_incidents_data,
            }.values()
        }

        for split_incident_sys_ids in [
            list(incident_sys_ids_mapping.keys())[i : i + AFFECTED_CIS_REQUEST_LIMIT]
            for i in range(0, len(incident_sys_ids_mapping.keys()), AFFECTED_CIS_REQUEST_LIMIT)
        ]:
            try:
                affected_cis.extend(
                    self.api_client.get_incidents_affected_cis(split_incident_sys_ids)
                )

            except ServiceNowRecordNotFoundException:
                self.logger.info("Affected CIs not found in ServiceNow")

        for affected_ci in affected_cis:
            affected_ci_mapping = self._affected_cis_mapping.get(affected_ci.sys_id, {})

            self._affected_cis_mapping[affected_ci.sys_id] = {
                "incident_numbers": list(
                    set(
                        affected_ci_mapping.get("incident_numbers", [])
                        + [incident_sys_ids_mapping.get(affected_ci.incident_sys_id)]
                    )
                ),
                "incident_sys_ids": list(
                    set(
                        affected_ci_mapping.get("incident_sys_ids", [])
                        + [affected_ci.incident_sys_id]
                    )
                ),
            }

    def get_affected_cis_details(self, sys_ids, datetime=None):
        """Get affected cis details

        Args:
            sys_ids ([str]): list of affected cis sys_ids
            datetime (datetime): datetime filter

        Returns:
            [AffectedCIDetails]: list of AffectedCIDetails objects
        """
        sn_format_timestamp = (
            self.api_client.convert_datetime_to_sn_format(datetime) if datetime else None
        )

        try:
            affected_cis_details = self.api_client.get_affected_cis_details(
                sys_ids, updated_on=sn_format_timestamp
            )
        except ServiceNowRecordNotFoundException:
            self.logger.info("Affected CIs details not found in ServiceNow")
            affected_cis_details = []

        return affected_cis_details

    def add_comments(self):
        """Add comments to case"""
        for incident_number, scope_ids in {
            **self._cached_incident_numbers_mapping,
            **self._incident_numbers_mapping,
        }.items():
            for scope_id in scope_ids:
                if self._incidents_changes.get(incident_number):
                    for key, change in self._incidents_changes.get(incident_number).items():
                        self.logger.info(f"Adding comment about changes to {scope_id} case")
                        try:
                            self.soar_job.add_comment(
                                comment=format_text(
                                    text="{prefix} Incident {incident_number} field "
                                    '{key} has been updated. "{old}" -> "{new}"',
                                    prefix=SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
                                    incident_number=incident_number,
                                    key=key,
                                    old=change[0],
                                    new=change[1],
                                ),
                                case_id=scope_id,
                                alert_identifier=None,
                            )
                        except Exception as e:
                            self.logger.info(
                                f"Failed to add comment about changes to {scope_id} "
                                f"case. Reason: {e}"
                            )

    def add_related_objects_changes_comments(self):
        """Add related objects changes comments to case"""
        related_objects_mapping = {
            **self._cached_related_objects_mapping,
            **self._related_objects_mapping,
        }
        incidents_mapping = {
            **self._cached_incident_numbers_mapping,
            **self._incident_numbers_mapping,
        }

        for link, changes in self._related_objects_changes.items():
            for key, change in changes.items():
                for incident_number in related_objects_mapping.get(link, {}).get(
                    "incident_numbers", []
                ):
                    for scope_id in incidents_mapping.get(incident_number, []):
                        self.logger.info(
                            f"Adding related object changes comment to {scope_id} case"
                        )
                        try:
                            self.soar_job.add_comment(
                                comment=format_text(
                                    text="{prefix} Incident {incident_number} "
                                    '"{object_key}" object with display name '
                                    '"{name}" has been updated. Affected Field: '
                                    '{key}. "{old}" -> "{new}"',
                                    prefix=SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
                                    incident_number=incident_number,
                                    object_key=related_objects_mapping.get(link, {}).get("key"),
                                    name=related_objects_mapping.get(link, {}).get("value"),
                                    key=key,
                                    old=change[0],
                                    new=change[1],
                                ),
                                case_id=scope_id,
                                alert_identifier=None,
                            )
                        except Exception as e:
                            self.logger.info(
                                f"Failed to add related object changes comment to "
                                f"{scope_id} case. Reason: {e}"
                            )

    def get_related_object(self, link):
        """Get related object

        Args:
            link (str): related object link

        Returns:
            dict: raw related object data
        """
        try:
            return self.api_client.get_additional_context_for_field(
                link, params={"sysparm_display_value": True}
            )
        except (ServiceNowRecordNotFoundException, ServiceNowNotFoundException):
            self.logger.info("Related object not found")
            return {}

    def get_updated_incident_affected_cis(self):
        """Get updated incident affected cis"""
        for sys_id, values in self._affected_cis_mapping.items():
            self._updated_incident_affected_cis.get("added", []).extend([
                (number, sys_id)
                for number in list(
                    set(values.get("incident_numbers", [])).difference(
                        self._cached_affected_cis_mapping.get(sys_id, {}).get(
                            "incident_numbers", []
                        )
                    )
                )
            ])

        for sys_id, values in self._cached_affected_cis_mapping.items():
            self._updated_incident_affected_cis.get("removed", []).extend([
                (number, sys_id)
                for number in list(
                    set(values.get("incident_numbers", [])).difference(
                        self._affected_cis_mapping.get(sys_id, {}).get("incident_numbers", [])
                    )
                )
            ])

    def add_affected_cis_changes_comments(self):
        """Add affected cis changes comments to case"""
        affected_cis_mapping = {
            **self._cached_affected_cis_mapping,
            **self._affected_cis_mapping,
        }
        affected_cis = {**self._cached_affected_cis, **self._affected_cis}
        incidents_mapping = {
            **self._cached_incident_numbers_mapping,
            **self._incident_numbers_mapping,
        }

        for key, items in self._updated_incident_affected_cis.items():
            for incident_number, affected_ci_sys_id in items:
                for scope_id in incidents_mapping.get(incident_number, []):
                    self.logger.info(
                        f"Adding incident affected CI changes comment to {scope_id} case"
                    )
                    try:
                        self.soar_job.add_comment(
                            comment=format_text(
                                text="{prefix} Incident {incident_number}. "
                                'Configuration item "{name}" has been {key}.',
                                prefix=SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
                                incident_number=incident_number,
                                name=affected_cis.get(affected_ci_sys_id, {}).get("name"),
                                key=key,
                            ),
                            case_id=scope_id,
                            alert_identifier=None,
                        )
                    except Exception as e:
                        self.logger.info(
                            f"Failed to add incident affected CI changes comment to "
                            f"{scope_id} case. Reason: {e}"
                        )

        for sys_id, changes in self._affected_cis_changes.items():
            for key, change in changes.items():
                for incident_number in affected_cis_mapping.get(sys_id, {}).get("incident_numbers"):
                    for scope_id in incidents_mapping.get(incident_number, []):
                        self.logger.info(f"Adding affected CI changes comment to {scope_id} case")
                        try:
                            self.soar_job.add_comment(
                                comment=format_text(
                                    text="{prefix} Incident {incident_number}. "
                                    'Configuration item "{name}" has been '
                                    "updated. Affected Field: {key}. "
                                    '"{old}" -> "{new}"',
                                    prefix=SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
                                    incident_number=incident_number,
                                    name=affected_cis.get(sys_id, {}).get("name"),
                                    key=key,
                                    old=change[0],
                                    new=change[1],
                                ),
                                case_id=scope_id,
                                alert_identifier=None,
                            )
                        except Exception as e:
                            self.logger.info(
                                f"Failed to add affected CI changes comment to"
                                f" {scope_id} case. Reason: {e}"
                            )

    def add_attachment_to_case(
        self,
        case_id: int,
        base64_blob: str,
        attachment_name: str,
    ) -> None:
        """Add attachment to case.

        Args:
            case_id (int): case id
            base64_blob (str): base64 blob of attachment
            attachment_name (str): attachment name
        """
        file_name, file_type = os.path.splitext(attachment_name)
        save_attachment_to_case_wall(
            self.soar_job,
            CaseWallAttachment(
                name=file_name,
                base64_blob=base64_blob,
                file_type=file_type,
                is_important=False,
                case_id=case_id,
            ),
        )

    def get_case_attachments(self, case_id, timestamp):
        """Get case attachments

        Args:
            case_id (int): case id
            timestamp (int): timestamp filter

        Returns:
            [dict]: list of raw attachments data
        """
        case_attachments = []

        try:
            wall_activities = get_case_attachments(self._soar_job, case_id)

            if isinstance(wall_activities, dict) and "activities" in wall_activities:
                for item in wall_activities.get("activities", []):
                    activity_data = json.loads(item.get("activityDataJson", "{}"))
                    if item.get("activityType") == "CaseComment" and activity_data.get("Type"):
                        if (
                            activity_data.get("Name", "").startswith(SNOW_ATTACHMENT_PREFIX)
                            or item.get("updateTime") < timestamp
                        ):
                            continue
                        case_attachments.append(activity_data)

            elif isinstance(wall_activities, list):
                for item in wall_activities:
                    if item.get("type") == CASE_ATTACHMENT_TYPE and item.get("fileType"):
                        if (
                            item.get("evidenceName", "").startswith(SNOW_ATTACHMENT_PREFIX)
                            or item.get("modificationTimeUnixTimeInMsForClient") < timestamp
                        ):
                            continue
                        case_attachments.append(item)

        except Exception as e:
            self.logger.info(f"Failed to get attachments for case {case_id}. Reason: {e}")

        return case_attachments

    def sync_utilities_snow_siem(self, datetime):
        """Sync utilities from snow to siem (comments, attachments)

        Args:
            datetime (datetime): datetime filter
        """
        sn_format_datetime = self.api_client.convert_datetime_to_sn_format(datetime)

        for incident_raw_data in self._updated_incidents_data.values():
            # sync comments from snow to siem
            self.sync_comments_snow_siem(incident_raw_data, sn_format_datetime)

            # sync attachments from snow to siem
            self.sync_attachments_snow_siem(incident_raw_data, sn_format_datetime)

    def sync_attachments_snow_siem(self, incident_raw_data, datetime):
        """Sync attachments from snow to siem

        Args:
            incident_raw_data (dict): raw incident data
            datetime (datetime): datetime filter
        """
        self.logger.info(f"Getting incident {incident_raw_data.get('number')} attachments")
        incident_attachments = self.api_client.get_incident_attachments_by_datetime(
            incident_raw_data.get("sys_id"), datetime
        )

        for incident_attachment in incident_attachments:
            if incident_attachment.filename.startswith(SIEM_ATTACHMENT_PREFIX):
                continue

            try:
                # getting attachment content
                content = self.api_client.get_attachment_content(
                    download_link=incident_attachment.download_link
                )
            except ServiceNowException as err:
                self.logger.error(
                    f"Failed to get {incident_attachment.filename} file content. Reason: {err}"
                )
                continue

            encoded_content = base64.b64encode(content).decode("ascii")

            #  adding attachment to cases
            for scope_id in self._cached_incident_numbers_mapping.get(
                incident_raw_data.get("number")
            ):
                try:
                    self.add_attachment_to_case(
                        scope_id,
                        encoded_content,
                        f"{SNOW_ATTACHMENT_PREFIX} {incident_attachment.filename}",
                    )
                    self.logger.info(f"Successfully added new attachment to {scope_id} case")
                except Exception as err:
                    self.logger.error(
                        f"Failed to attach file {incident_attachment.filename} to "
                        f"{scope_id} case. Reason: {err}"
                    )
                    continue

    def sync_comments_snow_siem(self, incident_raw_data, datetime):
        """Sync comments from snow to siem

        Args:
            incident_raw_data (dict): raw incident data
            datetime (datetime): datetime filter
        """
        try:
            self.logger.info(f"Getting incident {incident_raw_data.get('number')} comments")
            incident_comments = self.api_client.get_incident_comments_by_datetime(
                incident_raw_data.get("sys_id"), datetime
            )
        except ServiceNowRecordNotFoundException:
            self.logger.info(
                f"Comments for incident {incident_raw_data.get('number')} not found in ServiceNow"
            )
            incident_comments = []

        filtered_case_comments = self.filter_comments_by_prefix(
            [incident_comment.raw_data for incident_comment in incident_comments],
            "value",
            SIEM_COMMENT_PREFIX,
        )

        for comment in filtered_case_comments:
            for scope_id in self._cached_incident_numbers_mapping.get(
                incident_raw_data.get("number")
            ):
                self.logger.info(f"Adding comment to {scope_id} case")
                try:
                    self.soar_job.add_comment(
                        comment=f"{SNOW_COMMENT_PREFIX} Incident "
                        f"{incident_raw_data.get('number')}. "
                        f"{comment.get('value')}",
                        case_id=scope_id,
                        alert_identifier=None,
                    )
                except Exception as e:
                    self.logger.info(f"Failed to add comment to {scope_id} case. Reason: {e}")

    def sync_utilities_siem_snow(self, timestamp):
        """Sync utilities from siem to snow (comments, attachments)

        Args:
            timestamp (timestamp): timestamp filter
        """
        cached_case_ids = []

        for case_ids in self._cached_incident_numbers_mapping.values():
            cached_case_ids.extend(case_ids)

        cached_case_ids = list(set(cached_case_ids))

        for case_id in cached_case_ids:
            # sync comments from siem to snow
            self.sync_comments_siem_snow(case_id, timestamp)

            # sync attachments from siem to snow
            self.sync_attachments_siem_snow(case_id, timestamp)

    def sync_attachments_siem_snow(self, case_id, timestamp):
        """Sync attachments from siem to snow

        Args:
            case_id (int): case id
            timestamp (timestamp): timestamp filter
        """
        self.logger.info(f"Getting case {case_id} attachments")
        case_attachments = self.get_case_attachments(case_id, timestamp) or []
        self.logger.info(f"Found {len(case_attachments)} attachments in {case_id} case")

        for case_attachment in case_attachments:
            try:
                attachment_content = self._soar_job.get_attachment(
                    case_attachment.get("evidenceId")
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to get attachment with id "
                    f"{case_attachment.get('evidenceId')} from {case_id} case. "
                    f"Reason: {e}"
                )
                continue

            file_name = (
                f"{SIEM_ATTACHMENT_PREFIX} "
                f"{case_attachment.get('evidenceName')}"
                f"{case_attachment.get('fileType')}"
            )
            content_type = mimetypes.guess_type(file_name)[0]

            for (
                incident_number,
                case_ids,
            ) in self._cached_incident_numbers_mapping.items():
                try:
                    if case_id in case_ids:
                        self.api_client.add_attachment_to_incident(
                            self._cached_incidents_data.get(incident_number).get("sys_id"),
                            file_name,
                            attachment_content,
                            content_type,
                        )
                        # seek back to the beginning of the io.BitesIO object
                        attachment_content.seek(0)
                except Exception as e:
                    self.logger.error(
                        f"Failed to add attachment with id "
                        f"{case_attachment.get('evidenceId')} to {incident_number} "
                        f"incident. Reason: {e}"
                    )
                    continue

    def sync_comments_siem_snow(self, case_id, timestamp):
        """Sync comments from siem to snow

        Args:
            case_id (int): case id
            timestamp (timestamp): timestamp filter
        """
        siem_cases_comments = {}

        try:
            self.logger.info(f"Getting case {case_id} comments")
            case_comments = self.soar_job.fetch_case_comments(
                case_id, time_filter_type=0, from_timestamp=timestamp
            )
            self.logger.info(f"Found {len(case_comments)} comments in {case_id} case")

        except Exception as e:
            self.logger.info(f"Failed to fetch {case_id} case comments. Reason: {e}")
            case_comments = []

        filtered_case_comments = self.filter_comments_by_prefix(
            case_comments,
            "comment",
            (
                SNOW_COMMENT_PREFIX,
                SYNC_INCIDENTS_JOB_COMMENT_PREFIX,
                SNOW_ATTACHMENT_PREFIX,
            ),
        )

        siem_cases_comments[case_id] = filtered_case_comments

        for identifier, comments in siem_cases_comments.items():
            for comment in comments:
                for (
                    incident_number,
                    case_ids,
                ) in self._cached_incident_numbers_mapping.items():
                    if identifier in case_ids:
                        self.api_client.add_comment_to_incident(
                            incident_number,
                            f"{SIEM_COMMENT_PREFIX} {comment.get('comment')}",
                        )

    @staticmethod
    def filter_comments_by_prefix(comments, key, prefixes_to_except):
        """Filter comments excluding the ones with the provided prefixes

        Args:
            comments ([dict]): list of raw comments data
            key (str): key to get comment text
            prefixes_to_except ([str]): list of prefixes to exclude

        Returns:
            [dict]: list of filtered comments
        """
        return [
            comment
            for comment in comments
            if comment.get(key, "") and not comment.get(key, "").startswith(prefixes_to_except)
        ]

    def set_cache_data(self):
        """Set data in cache"""
        self.logger.info("Setting incident numbers mapping cache")
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=INCIDENT_NUMBERS_MAPPING_KEY,
            property_value=json.dumps({
                **self._cached_incident_numbers_mapping,
                **self._incident_numbers_mapping,
            }),
        )

        self.logger.info("Setting incidents related objects mapping cache")
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=RELATED_OBJECTS_MAPPING_KEY,
            property_value=json.dumps({
                **self._cached_related_objects_mapping,
                **self._related_objects_mapping,
            }),
        )

        self.logger.info("Setting incidents affected CIs mapping cache")
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=AFFECTED_CIS_MAPPING_KEY,
            property_value=json.dumps({**self._affected_cis_mapping}),
        )

        self.logger.info("Setting incidents cache")
        incidents = {
            **self._cached_incidents_data,
            **self._incidents_data,
            **self._updated_incidents_data,
        }

        set_chunks_as_job_context_property(
            self.soar_job,
            self.name_id,
            INCIDENTS_KEY,
            split_dict_into_chunks(incidents, chunk_size=INCIDENTS_CONTEXT_VALUE_CHUNK_SIZE),
        )

        self.logger.info("Setting related objects cache")
        related_objects = {
            key: value
            for key, value in {
                **self._cached_related_objects,
                **self._related_objects,
                **self._updated_related_objects_data,
            }.items()
            if value
        }

        set_chunks_as_job_context_property(
            self.soar_job,
            self.name_id,
            RELATED_OBJECTS_KEY,
            split_dict_into_chunks(
                related_objects, chunk_size=RELATED_OBJECTS_CONTEXT_VALUE_CHUNK_SIZE
            ),
        )

        self.logger.info("Setting affected CIs cache")
        affected_cis_details = {
            key: value
            for key, value in {
                **self._cached_affected_cis,
                **self._affected_cis,
                **self._updated_affected_cis,
            }.items()
            if key in self._affected_cis_mapping
        }

        set_chunks_as_job_context_property(
            self.soar_job,
            self.name_id,
            AFFECTED_CIS_KEY,
            split_dict_into_chunks(
                affected_cis_details, chunk_size=AFFECTED_CIS_CONTEXT_VALUE_CHUNK_SIZE
            ),
        )

    def _validate_params(self) -> None:
        """Validate job params"""
        validator = ParameterValidator(self.soar_job)
        validator.validate_ddl(
            param_name="Sync Level",
            value=self.params.sync_level,
            ddl_values=list(SYNC_LEVEL.values()),
            case_sensitive=True,
        )

    def _init_api_clients(self) -> "ServiceNowManager":
        """Initialize ServiceNow Manager."""
        try:
            sn_auth_params = ServiceNowAuthParams.build_from_job(self.soar_job)
            manager = ServiceNowManager(
                api_root=sn_auth_params.api_root,
                username=sn_auth_params.username,
                password=sn_auth_params.password,
                verify_ssl=sn_auth_params.verify_ssl,
                siemplify_logger=self.soar_job,
            )

            return manager

        except Exception as e:
            self.logger.error(f"Failed to initialize API clients: {e}")
            raise

    def _perform_job(self) -> None:
        """Perform the main flow of job"""
        last_run_timestamp = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_backwards},
            time_format=UNIX_FORMAT,
        )
        last_run_datetime = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_backwards}
        )
        processed_cases_last_run_timestamp = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_backwards},
            time_format=UNIX_FORMAT,
            timestamp_key=PROCESSED_CASES_TIMESTAMP_KEY,
        )
        self.logger.info(f"Last successful execution timestamp: {last_run_timestamp}")

        # getting data from cache
        self.get_cache_data()

        self.logger.info("Getting incident numbers mapping from SOAR")
        self.get_incident_numbers_mapping(processed_cases_last_run_timestamp)

        self.logger.info("Getting new incidents data from ServiceNow to cache")
        new_incident_numbers_to_cache = list(
            set(self._incident_numbers_mapping.keys())
            - set(self._cached_incident_numbers_mapping.keys())
        )
        if new_incident_numbers_to_cache:
            for incident in self.get_incidents(new_incident_numbers_to_cache):
                self._incidents_data[incident.number] = incident.raw_data

            self.logger.info(f"Fetched {len(self._incidents_data)} incidents data from ServiceNow")

            for number, incident_data in self._incidents_data.items():
                self.logger.info(f"Getting incident {number} related objects")
                self.get_incident_related_objects_mapping(incident_data)

        self.logger.info("Getting incidents affected CIs mapping")
        self.get_incident_affected_cis_mapping()

        self.logger.info("Getting updated incident Affected CIs")
        if self._cached_incident_numbers_mapping:
            self.get_updated_incident_affected_cis()

        self.logger.info("Getting incidents affected CIs")
        self._affected_cis = {
            affected_ci.sys_id: affected_ci.raw_data
            for affected_ci in self.get_affected_cis_details(
                list(self._affected_cis_mapping.keys())
            )
        }

        self.logger.info("Getting updated incidents data from ServiceNow to compare")
        if self._cached_incident_numbers_mapping:
            for incident in self.get_incidents(
                list(self._cached_incident_numbers_mapping.keys()),
                last_run_datetime,
            ):
                self._updated_incidents_data[incident.number] = incident.raw_data

            self.logger.info(
                f"Fetched {len(self._updated_incidents_data)} updated incidents data "
                f"from ServiceNow"
            )

        for number, updated_incident_data in self._updated_incidents_data.items():
            if self._cached_incidents_data.get(number):
                self.logger.info(f"Getting incident {number} related objects")
                self.get_incident_related_objects_mapping(updated_incident_data)

                self.logger.info("Comparing cached and updated incidents data")
                self._incidents_changes[number] = compare_nested_dicts(
                    self._cached_incidents_data.get(number),
                    updated_incident_data,
                    FIELDS_TO_EXCLUDE,
                )

        self.logger.info("Getting incident related objects data from ServiceNow to cache")
        for link in self._related_objects_mapping:
            self._related_objects[link] = self.get_related_object(link)

        self.logger.info(f"Fetched {len(self._related_objects)} related objects from ServiceNow")

        self.logger.info("Getting updated related objects data from ServiceNow to compare")
        for key in self._cached_related_objects_mapping.keys():
            self._updated_related_objects_data[key] = self.get_related_object(key)

        self.logger.info(
            f"Fetched {len(self._updated_incidents_data)} updated incidents data from ServiceNow"
        )

        self.logger.info("Getting updated Affected CIs from ServiceNow to compare")
        self._updated_affected_cis = {
            updated_affected_ci.sys_id: updated_affected_ci.raw_data
            for updated_affected_ci in self.get_affected_cis_details(
                list(self._cached_affected_cis_mapping.keys()),
                datetime=last_run_datetime,
            )
        }

        self.logger.info(
            f"Fetched {len(self._updated_affected_cis)} updated Affected CIs from ServiceNow"
        )

        self.logger.info("Comparing related objects data")
        for key in self._cached_related_objects_mapping.keys():
            if self._updated_related_objects_data.get(key):
                self._related_objects_changes[key] = compare_nested_dicts(
                    self._cached_related_objects.get(key),
                    self._updated_related_objects_data.get(key),
                    FIELDS_TO_EXCLUDE,
                )

        self.logger.info("Comparing Affected CIs")
        for key in self._cached_affected_cis_mapping.keys():
            if self._updated_affected_cis.get(key):
                self._affected_cis_changes[key] = compare_nested_dicts(
                    self._cached_affected_cis.get(key),
                    self._updated_affected_cis.get(key),
                    FIELDS_TO_EXCLUDE,
                )

        self.logger.info("Syncing utilities ServiceNow -> SIEM")
        self.sync_utilities_snow_siem(last_run_datetime)

        self.logger.info("Syncing utilities SIEM -> ServiceNow")
        self.sync_utilities_siem_snow(last_run_timestamp)

        if self._incidents_changes:
            self.logger.info("Adding comments about changes to cases")
            self.add_comments()

        if self._related_objects_changes:
            self.logger.info("Adding comments about changes in related objects to cases")
            self.add_related_objects_changes_comments()

        if self._affected_cis_changes or self._updated_incident_affected_cis:
            self.logger.info("Adding comments about changes in affected CIs to cases")
            self.add_affected_cis_changes_comments()

        # setting data in cache
        self.set_cache_data()

        self.logger.info("Saving timestamps")
        self._save_timestamp_by_unique_id(new_timestamp=self.job_start_time)

        self._save_timestamp_by_unique_id(
            new_timestamp=(
                list(self._processed_case_ids_mapping.values())[-1]
                if self._processed_case_ids_mapping
                else self.job_start_time
            ),
            timestamp_key=PROCESSED_CASES_TIMESTAMP_KEY,
        )


def main() -> None:
    SyncIncidentsJob(SYNC_INCIDENTS_JOB_NAME).start()


if __name__ == "__main__":
    main()
