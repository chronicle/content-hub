# Copyright 2026 Google LLC
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

import datetime
from functools import lru_cache
from typing import TYPE_CHECKING
import pytz

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.base.job import Job
from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.data_models import (
    CaseDataStatus,
    CaseDetails,
)

from TIPCommon.filters import filter_old_ids
from TIPCommon.rest.soar_api import (
    add_tags_to_case_in_bulk,
    get_case_overview_details,
    remove_case_tag,
)
from TIPCommon.smp_io import read_content, write_content
from TIPCommon.smp_time import validate_timestamp
from ..core.constants import (
    CASE_STATUS,
    CASES_SYNC_LIMIT,
    COMMENTS_MODIFICATION_TIME_FILTER,
    INCIDENTS_JOB_IDS_DB_KEY,
    INCIDENTS_JOB_IDS_FILE_NAME,
    INCIDENTS_LIMIT,
    INCIDENT_RESOLVED_STATUS,
    INCREMENT_CASE_UPDATED_TIME_BY_MS,
    MAX_TAG_LEN,
    MIN_TAG_LEN,
    MISSING_APPLICATION_ROLE_ERROR,
    SECOPS_CASE_TAG,
    SECOPS_COMMENT_PREFIX,
    SENTINEL_COMMENTS_LIMIT,
    SENTINEL_COMMENT_PREFIX,
    SENTINEL_TAG_PREFIX,
    SECOPS_TAG_PREFIX,
    SYNC_INCIDENTS_CONTEXT_IDENTIFIER,
    SYNC_INCIDENTS_JOB_NAME,
    SYNC_INCIDENTS_TIMEOUT_IN_MILLISECONDS,
    TIMESTAMP_FORMAT,
)
from ..core.exceptions import MicrosoftAzureSentinelManagerError, TimeoutIsApproachingError
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core import utils

if TYPE_CHECKING:
    from typing import NoReturn
    from TIPCommon.types import SingleJson


CaseIncidentMap = dict[str, list[str]]
SyncedPairs = list[tuple[str, str]]


class SyncIncidents(Job):
    def __init__(self) -> None:
        super().__init__(SYNC_INCIDENTS_JOB_NAME)
        self.manager: MicrosoftAzureSentinelManager | None = None
        self.last_processed_case_timestamp_in_ms: int | None = None
        self.last_processed_case_timestamp: datetime.datetime | None = None
        self.processed_case_data: CaseIncidentMap = {}
        self.current_run_latest_timestamp: int = 0
        self.timeout_in_milliseconds: int = SYNC_INCIDENTS_TIMEOUT_IN_MILLISECONDS
        self._start_time: datetime.datetime = datetime.datetime.now()

    @lru_cache(maxsize=128)
    def _get_cached_case_overview_details(self, case_id: str) -> CaseDetails:
        """Gets case overview details with memoization."""
        return get_case_overview_details(self.soar_job, case_id)

    def is_timeout_reached(self) -> bool:
        """
        Checks if the job has exceeded its timeout limit.
        Returns:
            bool: True if timeout is reached, False otherwise.
        """
        time_passed = (
            datetime.datetime.now() - self._start_time
        ).total_seconds() * NUM_OF_MILLI_IN_SEC
        return time_passed > self.timeout_in_milliseconds

    def _init_api_clients(self) -> None:
        """Initializes manager based on job parameters."""
        self.manager = MicrosoftAzureSentinelManager(
            api_root=self.params.api_root,
            login_url=self.params.oauth2_login_endpoint_url,
            tenant_id=self.params.azure_active_directory_id,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            verify_ssl=self.params.verify_ssl,
            siemplify=self.soar_job,
        )

    def _update_latest_timestamp(self, new_timestamp: int) -> None:
        """Helper method to update the timestamp if a newer one is found."""
        if new_timestamp > self.current_run_latest_timestamp:
            self.current_run_latest_timestamp = new_timestamp

    def _perform_job(self) -> None:
        """Executes the main synchronization logic."""
        try:
            last_run_timestamp = self.soar_job.fetch_timestamp(datetime_format=True)
            max_hours_backwards: int = self.params.max_hours_backwards
            self.last_processed_case_timestamp = validate_timestamp(
                last_run_timestamp, max_hours_backwards
            )
            self.last_processed_case_timestamp_in_ms = int(
                self.last_processed_case_timestamp.timestamp() * NUM_OF_MILLI_IN_SEC
            )
            self.last_processed_case_timestamp = (
                self.last_processed_case_timestamp.astimezone(pytz.utc)
            )
            self.logger.info(
                "Last successful case execution time: "
                f"{self.last_processed_case_timestamp}"
            )

            self.current_run_latest_timestamp = convert_datetime_to_unix_time(
                self.last_processed_case_timestamp
            )
            self.processed_case_data = self._read_cases().copy()
            self._add_new_or_modified_cases()

            self._sync_to_sentinel()
            self._sync_from_sentinel()

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.error(f"Failed job sync. {e}")
            raise

        except TimeoutIsApproachingError:
            self.logger.info("Job is about to time out. Saving progress and exiting.")

        finally:
            self._write_cases(self.processed_case_data)
            self.soar_job.save_timestamp(
                new_timestamp=self.current_run_latest_timestamp
            )
            self.logger.info(f"Saving timestamp: {self.current_run_latest_timestamp}")

    def _add_new_or_modified_cases(self) -> None:
        """
        Finds new cases, extracts their Sentinel incident IDs, and adds them
        to the database dictionary in the format {case_id: ["incident ids"]}.
        """
        all_relevant_case_ids = self._get_all_relevant_cases_ids()
        current_case_ids = set(self.processed_case_data)
        new_case_ids = filter_old_ids(all_relevant_case_ids, current_case_ids)
        for case_id in new_case_ids:
            try:
                case_details = self._get_cached_case_overview_details(case_id)
                incident_ids = self._extract_incident_ids_from_secops_case(case_details)
                if incident_ids:
                    self.processed_case_data[case_id] = incident_ids

            except MicrosoftAzureSentinelManagerError as e:
                self.logger.info(
                    f"Could not retrieve details for new case {case_id}. Skipping. "
                    f"Error: {e}"
                )

    def _get_all_relevant_cases_ids(self) -> list[str]:
        """Fetches new and modified cases from Google SecOps."""
        environment_name = self.params.environment_name

        start_time_ms = (
            convert_datetime_to_unix_time(self.last_processed_case_timestamp)
            + INCREMENT_CASE_UPDATED_TIME_BY_MS
        )

        case_ids = self.soar_job.get_cases_ids_by_filter(
            tags=[SECOPS_CASE_TAG],
            status=CASE_STATUS,
            update_time_from_unix_time_in_ms=start_time_ms,
            environments=[str(environment_name)],
        )

        all_relevant_case_ids = list({str(case_id) for case_id in case_ids})
        self.logger.info(
            f"Found {len(all_relevant_case_ids)} new/modified case IDs: "
            f"{all_relevant_case_ids}"
        )
        return all_relevant_case_ids

    def _sync_to_sentinel(self) -> None:
        """Synchronizes changes from Google SecOps to Microsoft Sentinel."""
        try:
            cases_to_sync_to_sentinel = []
            for case_id in self.processed_case_data:
                if self.is_timeout_reached():
                    raise TimeoutIsApproachingError
                try:
                    case_details = self._get_cached_case_overview_details(case_id)
                    last_update_ms = case_details.modification_time_unix_time_ms
                    if last_update_ms > convert_datetime_to_unix_time(
                        self.last_processed_case_timestamp
                    ):
                        cases_to_sync_to_sentinel.append(case_id)

                except MicrosoftAzureSentinelManagerError as e:
                    self.logger.info(
                        f"Could not retrieve details for case {case_id}. Skipping. "
                        f"Error: {e}"
                    )

            cases_to_sync_to_sentinel = cases_to_sync_to_sentinel[:CASES_SYNC_LIMIT]

            self.logger.info(
                f"Processing {len(cases_to_sync_to_sentinel)} cases "
                "for sync to Sentinel."
            )

            for case_id in cases_to_sync_to_sentinel:
                if self.is_timeout_reached():
                    raise TimeoutIsApproachingError

                self._process_secops_case(case_id)
                self._get_cached_case_overview_details.cache_clear()
                try:
                    case_details = self._get_cached_case_overview_details(case_id)
                    self._update_latest_timestamp(
                        case_details.modification_time_unix_time_ms
                    )

                except MicrosoftAzureSentinelManagerError as e:
                    self.logger.info(
                        f"Could not retrieve final details for case {case_id}: {e}"
                    )

        except MicrosoftAzureSentinelManagerError as e:
            if MISSING_APPLICATION_ROLE_ERROR.lower() in str(e).lower():
                self.logger.error(f"Failed to sync case to Sentinel. Error: {e}")
                raise
            raise

    def _process_secops_case(self, case_id: str) -> None:
        """Synchronization of a single Google SecOps case to Microsoft Sentinel."""
        try:
            case = self._get_cached_case_overview_details(case_id)
            incident_ids = self._extract_incident_ids_from_secops_case(case)
            if not incident_ids:
                self.logger.info(
                    f"No Sentinel incident IDs found for Google SecOps case {case_id}. "
                    "Skipping."
                )
                return

            incidents = self.manager.get_incidents_by_id(list(incident_ids))

            for incident in incidents:
                incident_id = incident.get("id")
                self._sync_case_comments_to_sentinel(case_id, incident_id)
                self._sync_case_tags_to_sentinel(case, incident, incident_id)

                if self._sync_case_status_to_sentinel(
                    case, case_id, incident, incident_id
                ):
                    self._remove_synced_entries(
                        id_map=self.processed_case_data,
                        synced_list=[(case_id, incident_id)],
                    )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                f"Failed to process SecOps case for sync to Sentinel. Error: {e}"
            )

    def _sync_case_status_to_sentinel(
        self,
        case: CaseDetails,
        case_id: str,
        incident: SingleJson,
        incident_id: str,
    ) -> bool:
        """
        Syncs the status from a Google SecOps case to a Microsoft Sentinel incident.
        Args:
            case (CaseDetails): The Google SecOps case details.
            case_id (str): The ID of the Google SecOps case.
            incident_id (str): The ID of the Microsoft Sentinel incident.
        Returns:
            bool: True if the incident status was successfully updated in Sentinel,
                    False otherwise.
        """
        closure_reason: str | None = None

        if case.status == CaseDataStatus.CLOSED:
            closure_reason = self.soar_job.get_case_closure_details([str(case_id)])[
                0
            ].get("reason", "")

        else:
            alert_details = next(
                (
                    alert
                    for alert in case.alerts
                    if utils.get_incident_id_from_alert(self.soar_job, alert)
                    == incident_id
                ),
                None,
            )

            if (
                alert_details
                and alert_details.status == "Close"
                and len(case.alerts) > 1
            ):
                try:
                    closure_reason = alert_details.closure_details.get("reason")

                except AttributeError:
                    self.logger.error(
                        f"Alert {alert_details.identifier} is closed "
                        "but closureDetails is missing."
                    )
                    return False

        if closure_reason:
            try:
                if incident.get("status") != INCIDENT_RESOLVED_STATUS:
                    classification, determination = self._get_sentinel_closure_details(
                        closure_reason
                    )
                    self.manager.update_incident_status(
                        incident_id=incident_id,
                        status=INCIDENT_RESOLVED_STATUS,
                        classification=classification,
                        determination=determination,
                    )
                return True

            except MicrosoftAzureSentinelManagerError as e:
                self.logger.info(
                    f"Failed to update incident status for {incident_id}. Error: {e}"
                )
                return False

        return False

    def _get_sentinel_closure_details(
        self,
        case_closure_reason: str,
    ) -> tuple[str, str]:
        """
        Maps Google SecOps closure reason to Sentinel classification and
        determination.
        Returns:
            A tuple containing the Sentinel classification and determination.
        """
        mapping: dict[str, tuple[str, str]] = {
            "Malicious": ("truePositive", "maliciousUserActivity"),
            "NotMalicious": ("falsePositive", "other"),
        }

        closure_details = mapping.get(case_closure_reason)

        if closure_details:
            return closure_details

        self.logger.warn(
            "Could not find a Sentinel closure mapping for Google SecOps "
            f"reason: '{case_closure_reason}'. Defaulting to 'unknown'."
        )
        return "unknown", "unknown"

    def _sync_case_comments_to_sentinel(self, case_id: str, incident_id: str) -> None:
        """
        Syncs comments from a Google SecOps case to a Microsoft Sentinel incident.
        Args:
            case_id: The ID of the Google SecOps case.
            incident_id: The ID of the Microsoft Sentinel incident.
        """
        try:
            secops_comments = self.soar_job.fetch_case_comments(
                case_id=case_id,
                time_filter_type=COMMENTS_MODIFICATION_TIME_FILTER,
                from_timestamp=self.last_processed_case_timestamp_in_ms,
            )

            if not secops_comments:
                return

            def is_valid_comment(comment: SingleJson) -> bool:
                content = comment.get("comment", "").strip()
                return bool(content) and not content.startswith(SENTINEL_COMMENT_PREFIX)

            valid_comments = [
                f"{SECOPS_COMMENT_PREFIX}{c['comment']}"
                for c in secops_comments
                if is_valid_comment(c)
            ]

            if not valid_comments:
                return

            for comment in valid_comments:
                self.manager.add_comment_to_graph_incident(incident_id, comment)

            if valid_comments:
                self.logger.info(
                    "Successfully synced comments from SecOps to Sentinel "
                    f"incident {incident_id}."
                )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                "Failed to sync comments from Google SecOps for case "
                f"{case_id}. Error: {e}"
            )

    def _is_tag_valid(
        self,
        stripped_tag: str,
        prefix_to_exclude: str,
        tag_to_exclude: str | None,
        min_len: int,
        max_len: int,
    ) -> bool:
        """Checks if a stripped tag meets all exclusion and length criteria."""
        if not stripped_tag:
            return False
        if tag_to_exclude and stripped_tag == tag_to_exclude:
            return False
        if stripped_tag.startswith(prefix_to_exclude):
            return False
        if len(stripped_tag) < min_len or len(stripped_tag) > max_len:
            return False

        return True

    def _get_new_tags(
        self,
        source_tags: list[str],
        existing_tags: list[str],
        prefix_to_add: str,
        prefix_to_exclude: str,
        tag_to_exclude: str | None = None,
        min_len: int = 0,
        max_len: int = float("inf"),
    ) -> list[str]:
        """
        Identifies tags from source_tags that should be added
        to the destination system.
        """
        new_tags = []

        for tag in source_tags:
            stripped_tag = tag.strip()

            if not self._is_tag_valid(
                stripped_tag,
                prefix_to_exclude,
                tag_to_exclude,
                min_len,
                max_len,
            ):
                continue

            prefixed_tag = f"{prefix_to_add}{stripped_tag}"
            if prefixed_tag not in existing_tags:
                new_tags.append(prefixed_tag)

        return new_tags

    def _get_tags_to_remove(
        self,
        source_tags: list[str],
        destination_tags: list[str],
        source_prefix: str,
    ) -> list[str]:
        """
        Identifies tags to be removed from the destination system.
        """
        tags_to_remove = []
        source_tags_prefixed = {f"{source_prefix}{tag}" for tag in source_tags}

        for dest_tag in destination_tags:
            if (
                dest_tag.startswith(source_prefix)
                and dest_tag not in source_tags_prefixed
            ):
                tags_to_remove.append(dest_tag)

        return tags_to_remove

    def _sync_case_tags_to_sentinel(
        self,
        case: CaseDetails,
        incident: SingleJson,
        incident_id: str,
    ) -> None:
        """
        Syncs tags from a Google SecOps case to a Microsoft Sentinel incident.
        Args:
            case: The CaseDetails object from Google SecOps.
            incident_id: The ID of the Microsoft Sentinel incident.
        """
        try:
            secops_tags = [
                tag.get("displayName") for tag in case.tags if isinstance(tag, dict)
            ]
            ms_tags = incident.get("customTags", [])

            tags_to_add = self._get_new_tags(
                source_tags=secops_tags,
                existing_tags=ms_tags,
                prefix_to_add=SECOPS_TAG_PREFIX,
                prefix_to_exclude=SENTINEL_TAG_PREFIX,
                tag_to_exclude=SECOPS_CASE_TAG,
            )
            tags_to_remove = self._get_tags_to_remove(
                source_tags=secops_tags,
                destination_tags=ms_tags,
                source_prefix=SECOPS_TAG_PREFIX,
            )

            if tags_to_add:
                combined_tags = list(set(ms_tags + tags_to_add))
                self.manager.add_tags_to_incident(incident_id, combined_tags)

            ms_tags = incident.get("customTags", [])

            if tags_to_remove:
                self.manager.remove_tags_from_incident(
                    incident_id, tags_to_remove, ms_tags
                )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                "Failed to sync tags to Sentinel for incident "
                f"{incident_id}. Error: {e}"
            )

    def _sync_from_sentinel(self) -> None:
        """Synchronizes changes from Microsoft Sentinel to Google SecOps."""
        incident_ids_to_case_map = {}
        for case_id, incident_ids in self.processed_case_data.items():
            if self.is_timeout_reached():
                raise TimeoutIsApproachingError

            try:
                case = self._get_cached_case_overview_details(case_id)
                for incident_id in incident_ids:
                    incident_ids_to_case_map[incident_id] = {
                        "case_id": case_id,
                        "case": case,
                    }

            except MicrosoftAzureSentinelManagerError as e:
                self.logger.info(f"Could not retrieve details for case {case_id}: {e}")

        unique_incident_ids = list(incident_ids_to_case_map.keys())

        if not unique_incident_ids:
            self.logger.info("No Sentinel incident IDs found for synchronization.")
            return

        try:
            incidents = self.manager.get_incidents_by_ids(
                incident_ids=unique_incident_ids,
                from_timestamp=self.last_processed_case_timestamp.strftime(
                    TIMESTAMP_FORMAT
                ),
                limit=INCIDENTS_LIMIT,
            )
            self.logger.info(
                f"Processing {len(incidents)} incidents for sync to Secops."
            )
            for incident in incidents:
                incident_id = incident.get("id")
                related_case_data = incident_ids_to_case_map.get(incident_id)
                if related_case_data:
                    case = related_case_data["case"]
                    case_id = related_case_data["case_id"]
                    self._process_sentinel_incident(incident, case, case_id)

        except MicrosoftAzureSentinelManagerError as e:
            if MISSING_APPLICATION_ROLE_ERROR.lower() in str(e).lower():
                self.logger.error(
                    f"Failed to fetch incidents from Sentinel. Error: {e}"
                )
                raise
            raise e

    def _process_sentinel_incident(
        self, incident: SingleJson, case: CaseDetails, case_id: str
    ) -> None:
        """Synchronization of Microsoft Sentinel incident to Google SecOps."""
        incident_id = incident.get("id")
        try:
            is_closed = self._close_secops_case_or_alert_if_incident_resolved(
                incident, case, case_id
            )

            if is_closed:
                self._remove_synced_entries(
                    id_map=self.processed_case_data,
                    synced_list=[(case_id, incident_id)],
                )

            self._sync_incident_comments_to_secops(
                incident_id,
                case,
                case_id,
            )
            self._sync_incident_tags_to_secops(incident, incident_id, case, case_id)
            self._get_cached_case_overview_details.cache_clear()
            try:
                updated_case_details = self._get_cached_case_overview_details(case_id)
                self._update_latest_timestamp(
                    updated_case_details.modification_time_unix_time_ms
                )

            except MicrosoftAzureSentinelManagerError as e:
                self.logger.info(
                    f"Could not retrieve final details for case {case_id}: {e}"
                )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                f"Failed to process Sentinel incident {incident_id} "
                f"for sync to SecOps. Error: {e}"
            )

    def _close_secops_case_or_alert_if_incident_resolved(
        self,
        incident: SingleJson,
        case: CaseDetails,
        case_id: str,
    ) -> bool:
        """
        Closes the Google SecOps case/alert if it's open and the matching
        Sentinel incident was resolved.
        Returns:
            bool: True if a close operation was performed, False otherwise.
        """
        incident_status = incident.get("status")

        if (
            incident_status == INCIDENT_RESOLVED_STATUS
            and case.status == CaseDataStatus.OPENED
        ):
            reason, root_cause = self._get_secops_closure_details(incident)

            alert_identifier = self._find_alert_identifier(case, incident.get("id"))
            if not alert_identifier:
                self.logger.info(
                    "Could not find a matching alert identifier for Sentinel "
                    f"incident {incident.get('id')}. Skipping closure."
                )
                return False

            try:
                self._close_alert(
                    case_id,
                    alert_identifier,
                    reason,
                    root_cause,
                    incident.get("id"),
                )
                return True

            except MicrosoftAzureSentinelManagerError:
                self.logger.info(
                    "Failed to close case or alert "
                    f"{alert_identifier} in case {case_id}."
                )

        return False

    def _get_secops_closure_details(self, incident: SingleJson) -> tuple[str, str]:
        """
        Maps Sentinel classification to Google SecOps closure reason and root cause.
        Returns:
            tuple[str, str]: A tuple containing the Google SecOps closure reason
            and root cause.
        """
        mapping: dict[str, tuple[str, str]] = {
            "truePositive": (
                "Malicious",
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            ),
            "falsePositive": (
                "NotMalicious",
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            ),
        }

        classification = mapping.get(
            incident.get("classification"),
            (
                "Inconclusive",
                CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
            ),
        )

        if incident.get("classification") not in mapping:
            self.logger.warn(
                f"Sentinel classification '{incident.get('classification')}' "
                "not found in mapping. Using default: Inconclusive."
            )

        return classification

    def _sync_incident_comments_to_secops(
        self,
        incident_id: str,
        case: CaseDetails,
        case_id: str,
    ) -> None:
        """
        Syncs comments from a Microsoft Sentinel incident to Google SecOps.
        Args:
            incident_id: The ID of the Microsoft Sentinel incident.
            case: The CaseDetails object representing the Google SecOps case.
            case_id: The ID of the Google SecOps case.
        """
        try:
            from_timestamp = self.last_processed_case_timestamp
            ms_comments = self.manager.get_incident_comments(
                incident_id,
                start_time=from_timestamp,
                limit=SENTINEL_COMMENTS_LIMIT,
            )

            if not ms_comments:
                return

            alert_identifier = self._find_alert_identifier(case, incident_id)

            valid_comments = [
                f"{SENTINEL_COMMENT_PREFIX}{utils.strip_html_tags(c)}"
                for c in ms_comments
                if self._is_valid_ms_comment(c)
            ]

            for comment in valid_comments:
                self.soar_job.add_comment(
                    case_id=case_id,
                    comment=comment,
                    alert_identifier=alert_identifier,
                )

            if valid_comments:
                self.logger.info(
                    "Successfully synced comments from Sentinel to Secops "
                    f"case {case_id}."
                )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                "Failed to sync comments from Sentinel for incident "
                f"{incident_id}. Error: {e}"
            )

    def _is_valid_ms_comment(self, comment: str) -> bool:
        """Checks if a Microsoft Sentinel comment should be synced to SecOps."""
        clean_comment = utils.strip_html_tags(comment)
        return not clean_comment.startswith(SECOPS_COMMENT_PREFIX)

    def _sync_incident_tags_to_secops(
        self,
        incident: SingleJson,
        incident_id: str,
        case: CaseDetails,
        case_id: str,
    ) -> None:
        """
        Syncs tags from a Microsoft Sentinel incident to Google SecOps.
        Args:
            incident_id: The ID of the Microsoft Sentinel incident.
            case: The CaseDetails object from Google SecOps.
            case_id: The ID of the Google SecOps case.
        """
        try:
            alert_identifier = self._find_alert_identifier(case, incident_id)
            if not alert_identifier:
                return

            ms_tags = incident.get("customTags", [])
            secops_tags = [
                tag.get("displayName") for tag in case.tags if isinstance(tag, dict)
            ]

            tags_to_add = self._get_new_tags(
                source_tags=ms_tags,
                existing_tags=secops_tags,
                prefix_to_add=SENTINEL_TAG_PREFIX,
                prefix_to_exclude=SECOPS_TAG_PREFIX,
                min_len=MIN_TAG_LEN,
                max_len=MAX_TAG_LEN,
            )
            tags_to_remove = self._get_tags_to_remove(
                source_tags=ms_tags,
                destination_tags=secops_tags,
                source_prefix=SENTINEL_TAG_PREFIX,
            )

            if tags_to_add:
                add_tags_to_case_in_bulk(self.soar_job, [int(case_id)], tags_to_add)
                self.logger.info(f"Successfully added tags to secops case {case_id}.")

            if tags_to_remove:
                for tag in tags_to_remove:
                    remove_case_tag(
                        chronicle_soar=self.soar_job,
                        case_id=int(case_id),
                        tag=tag,
                        alert_identifier=alert_identifier,
                    )
                self.logger.info(
                    f"Successfully removed tags from  secops case {case_id}"
                )

        except MicrosoftAzureSentinelManagerError as e:
            self.logger.info(
                f"Failed to sync tags to SecOps for incident {incident_id}. Error: {e}"
            )

    def _read_cases(self) -> CaseIncidentMap:
        """Reads processed case data from a file or database."""
        return read_content(
            siemplify=self.soar_job,
            file_name=INCIDENTS_JOB_IDS_FILE_NAME,
            db_key=INCIDENTS_JOB_IDS_DB_KEY,
            default_value_to_return={},
            identifier=SYNC_INCIDENTS_CONTEXT_IDENTIFIER,
        )

    def _write_cases(self, updated_cases: CaseIncidentMap) -> None:
        """
        Writes processed case data to a file or database,
        removing closed and fully resolved cases.
        """
        write_content(
            siemplify=self.soar_job,
            content_to_write=updated_cases,
            file_name=INCIDENTS_JOB_IDS_FILE_NAME,
            db_key=INCIDENTS_JOB_IDS_DB_KEY,
            identifier=SYNC_INCIDENTS_CONTEXT_IDENTIFIER,
        )

    def _remove_synced_entries(
        self,
        id_map: CaseIncidentMap,
        synced_list: SyncedPairs,
    ) -> None:
        """Removes entries from the ID map after successful synchronization."""
        for case_id, incident_id in synced_list:
            if case_id in id_map and incident_id in id_map[case_id]:
                id_map[case_id].remove(incident_id)
                if not id_map[case_id]:
                    id_map.pop(case_id, None)

    @lru_cache(maxsize=256)
    def _extract_incident_ids_from_secops_case(self, case: CaseDetails) -> list[str]:
        """
        Extracts Sentinel incident IDs from a Google SecOps case.
        Returns a deduplicated and sorted list.
        """
        incident_ids = []
        for alert in case.alerts:
            ticket_id = utils.get_incident_id_from_alert(self.soar_job, alert)
            if ticket_id:
                incident_ids.append(ticket_id)

        return sorted(set(incident_ids))

    @lru_cache(maxsize=256)
    def _find_alert_identifier(self, case: CaseDetails, incident_id: str) -> str | None:
        """Finds the alert identifier associated with a Sentinel incident ID."""
        for alert in case.alerts:
            extracted_incident_id = utils.get_incident_id_from_alert(
                self.soar_job, alert
            )
            if extracted_incident_id == incident_id:
                return alert.identifier

        return None

    def _close_alert(
        self,
        case_id: str,
        alert_identifier: str,
        reason: str,
        root_cause: str,
        incident_id: str,
    ) -> None:
        """Closes a specific alert within a Google SecOps case."""
        close_comment = (
            "Closed automatically due to Microsoft Sentinel incident status "
            f"change. Sentinel Incident ID: {incident_id}. Reason: {reason}"
        )

        self.soar_job.close_alert(
            root_cause=root_cause,
            comment=close_comment,
            reason=reason,
            case_id=case_id,
            alert_id=alert_identifier,
        )

        self.logger.info(
            f"Successfully closed alert {alert_identifier} in case {case_id}."
        )


def main() -> NoReturn:
    SyncIncidents().start()


if __name__ == "__main__":
    main()
