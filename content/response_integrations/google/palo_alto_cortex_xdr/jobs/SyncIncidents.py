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
import json
import enum
import itertools
from typing import TYPE_CHECKING
import math

import pytz
import requests
from requests.exceptions import JSONDecodeError
from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
)
from TIPCommon.base.job import Job
from TIPCommon.base.utils import is_native
from TIPCommon.data_models import (
    AlertCard,
    CaseDataStatus,
    CaseDetails,
)
from TIPCommon.rest.soar_api import (
    get_case_overview_details,
    get_cases_by_timestamp_filter,
)
from TIPCommon.smp_time import validate_timestamp

from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_unixtime_to_datetime,
    unix_now,
)
from palo_alto_cortex_xdr.core import constants
from palo_alto_cortex_xdr.core import utils
from palo_alto_cortex_xdr.core.auth import AuthenticatedSession
from palo_alto_cortex_xdr.core.exceptions import XDRException, TimeoutIsApproachingError
from palo_alto_cortex_xdr.core.XDRManager import ApiParameters, XDRManager

if TYPE_CHECKING:
    from typing import NoReturn
    from TIPCommon.types import SingleJson
    from palo_alto_cortex_xdr.core.datamodels import IncidentInfo, IncidentExtraData

SyncItem = list[str]
SyncData = dict[str, SyncItem]
CaseInfoList = list[tuple[str, int]]


class SyncIncidents(Job):
    def __init__(self) -> None:
        super().__init__(name=constants.SYNC_INCIDENTS_JOB_NAME)
        self.last_processed_case_timestamp: datetime.datetime | None = None
        self.processed_items: SyncData = {}
        self.case_details: dict[str, dict[str, CaseDetails | list[str]]] = {}
        self.last_run_timestamp_ms: int = 0
        self.current_run_latest_timestamp_ms: int = 0
        self.timeout_in_milliseconds: int = (
            constants.SYNC_INCIDENTS_TIMEOUT_IN_MILLISECONDS
        )
        self.sync_limit: int = constants.JOB_SYNC_LIMIT
        self.context_identifier = constants.SYNC_INCIDENTS_CONTEXT_IDENTIFIER
        self.tags = [constants.SECOPS_CASE_TAG]
        self.sorted_modified_ids: CaseInfoList = []

    def _init_api_clients(self) -> XDRManager:
        integration_params: utils.IntegrationParameters = (
            utils.get_integration_parameters(self.soar_job)
        )
        authenticator: AuthenticatedSession = AuthenticatedSession()
        session: requests.Session = authenticator.authenticate_session(
            integration_params
        )
        session.verify = integration_params.verify_ssl
        api_params: ApiParameters = ApiParameters(api_root=integration_params.api_root)
        self.manager = XDRManager(
            session=session,
            api_params=api_params,
            logger=self.logger,
        )
        self._api_client = self.manager

        return self.manager

    def _perform_job(self) -> None:
        try:
            self._initialize_run()
            self._discover_and_prepare_items()
            self._sync_soar_to_product()
            self._sync_product_to_soar()

        except XDRException:
            self.logger.info("Job is approaching timeout. Saving progress and exiting.")

        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during the sync cycle: {e}"
            )
            self.logger.exception(e)
            raise

        finally:
            self._finalize_run()

    def _initialize_run(self) -> None:
        last_run_timestamp: datetime.datetime
        last_run_timestamp = self._fetch_timestamp_by_unique_id(datetime_format=True)
        max_hours_backwards: int = self.params.max_hours_backwards
        self.last_processed_case_timestamp: datetime.datetime = validate_timestamp(
            last_run_timestamp,
            max_hours_backwards,
        )
        self.last_run_timestamp_ms = int(
            self.last_processed_case_timestamp.timestamp() * constants.MAX_LIMIT
        )
        self.last_processed_case_timestamp: datetime.datetime = (
            self.last_processed_case_timestamp.astimezone(pytz.utc)
        )
        self.logger.info(
            f"Last successful case execution time: {self.last_processed_case_timestamp}"
        )
        self.current_run_latest_timestamp_ms: int = convert_datetime_to_unix_time(
            self.last_processed_case_timestamp
        )
        self.processed_items: SyncData = self._read_state()

    def _discover_and_prepare_items(self) -> None:
        sorted_modified_ids: CaseInfoList = self._get_sorted_modified_case_ids()
        self.sorted_modified_ids = sorted_modified_ids[: self.sync_limit]
        self._process_and_store_case_details()

    def _get_sorted_modified_case_ids(self) -> CaseInfoList:
        cases_by_modified_timestamp: CaseInfoList = self._fetch_case_ids()
        modified_synced_case_ids: CaseInfoList = self._fetch_case_ids(
            list(self.processed_items),
        )
        sorted_modified_ids: CaseInfoList = utils.merge_and_sort(
            cases_by_modified_timestamp,
            modified_synced_case_ids,
        )

        if not is_native(self.modified_synced_case_ids_by_product):
            synced_incident_ids: list[str] = list(
                itertools.chain.from_iterable(self.processed_items.values())
            )
            modified_synced_case_ids_by_product: list[tuple[int, int]]
            modified_synced_case_ids_by_product = (
                self.modified_synced_case_ids_by_product(synced_incident_ids)
            )
            sorted_modified_ids: CaseInfoList = utils.merge_and_sort(
                sorted_modified_ids,
                modified_synced_case_ids_by_product,
            )

        return sorted_modified_ids

    def _process_and_store_case_details(self) -> None:
        for case_id, _ in self.sorted_modified_ids:
            try:
                case_details: CaseDetails = get_case_overview_details(
                    self.soar_job, case_id
                )
                case_details.alerts = case_details.alerts[::-1]
                incident_ids: list[str] = self._extract_product_ids_from_case(
                    case_details
                )
                self.processed_items[case_id] = incident_ids
                self.case_details[case_id] = {
                    "case": case_details,
                    "incident_ids": incident_ids,
                }

            except XDRException as e:
                self.logger.info(
                    f"Could not retrieve details for new case {case_id}. "
                    f"Skipping. Error: {e}"
                )

    def _sync_soar_to_product(self) -> None:
        try:
            cases_to_sync: CaseInfoList = self.sorted_modified_ids
            self.logger.info(
                f"Processing {len(cases_to_sync)} updated cases for sync to XDR."
            )

            all_incident_ids: set[str] = self._collect_incident_ids_from_cases(
                cases_to_sync,
            )

            incidents_map: dict[str, IncidentInfo] = self._fetch_and_map_incidents(
                all_incident_ids,
            )

            if not incidents_map:
                return

            self._process_cases_with_incidents(cases_to_sync, incidents_map)

        except XDRException as e:
            if constants.MISSING_PERMISSIONS_ERROR.lower() in str(e).lower():
                self.logger.error(f"Failed to sync case to XDR. Error: {e}")
                raise
            raise

    def _collect_incident_ids_from_cases(
        self,
        cases_to_sync: CaseInfoList,
    ) -> set[str]:
        all_incident_ids_to_fetch: set[str] = set()
        for case_id, _ in cases_to_sync:
            if self.is_timeout_reached():
                raise TimeoutIsApproachingError

            case_data: dict[str, CaseDetails | list[str]] | None = (
                self.case_details.get(case_id)
            )
            if case_data and case_data.get("incident_ids"):
                all_incident_ids_to_fetch.update(case_data["incident_ids"])

        return all_incident_ids_to_fetch

    def _fetch_and_map_incidents(
        self,
        incident_ids: set[str],
    ) -> dict[str, IncidentInfo]:
        if not incident_ids:
            self.logger.info("No XDR incident IDs found in any of the cases to sync.")
            return {}

        self.logger.info(f"Fetching {len(incident_ids)} incidents from XDR.")
        all_incidents: list[IncidentInfo] = self._call_manager(
            self.manager.get_incidents,
            incident_id_list=list(incident_ids),
        )

        incidents_map: dict[str, IncidentInfo] = {
            str(inc.raw_data.get(constants.XDR_INC_ID)): inc
            for inc in all_incidents
        }
        return incidents_map

    def _process_cases_with_incidents(
        self,
        cases_to_sync: CaseInfoList,
        incidents_map: dict[str, IncidentInfo],
    ) -> None:
        for case_id, _ in cases_to_sync:
            if self.is_timeout_reached():
                raise TimeoutIsApproachingError

            case_data: dict[str, CaseDetails | list[str]] | None = (
                self.case_details.get(case_id)
            )
            if not case_data:
                continue

            case: CaseDetails = case_data["case"]
            incident_ids_for_case: list[str] = case_data["incident_ids"]

            incidents_for_case: list[IncidentInfo] = [
                incidents_map[inc_id]
                for inc_id in incident_ids_for_case
                if inc_id in incidents_map
            ]

            self._process_secops_case(case, case_id, incidents_for_case)

    def _sync_product_to_soar(self) -> None:
        incident_ids_to_case_map: SingleJson = self._build_incident_to_case_map()
        self._fetch_and_process_xdr_incidents(incident_ids_to_case_map)

    def _finalize_run(self) -> None:
        self._write_state(self.processed_items)
        if len(self.sorted_modified_ids) > 0:
            self._save_timestamp_by_unique_id(
                new_timestamp=self.sorted_modified_ids[-1][1]
            )
            self.current_run_latest_timestamp_ms = self.sorted_modified_ids[-1][1]

        latest_time: int = self.current_run_latest_timestamp_ms
        self.logger.info(
            f"Saving timestamp: {latest_time} "
            f"[{convert_unixtime_to_datetime(latest_time)}]"
        )

    def _process_secops_case(
        self,
        case: CaseDetails,
        case_id: str,
        incidents: list[IncidentInfo],
    ) -> None:
        try:
            if not incidents:
                self.logger.info(
                    f"No XDR incidents found for Google SecOps case {case_id} after "
                    "fetching. Skipping."
                )
                return

            for incident in incidents:
                self._process_single_incident_for_case(case, case_id, incident)

        except (XDRException, JSONDecodeError) as e:
            self.logger.info(
                f"Failed to process SecOps case {case_id} for sync to XDR. Error: {e}"
            )

    def _process_single_incident_for_case(
        self,
        case: CaseDetails,
        case_id: str,
        incident: IncidentInfo,
    ) -> None:
        self._enrich_incident_with_alerts(incident)
        self._sync_secops_case_to_incident(case, case_id, incident)
        self._sync_case_owner_to_xdr(case, incident)

        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        incident_alerts: list[SingleJson] = incident.raw_data.get("alerts", [])
        self._save_xdr_alerts_to_context(case, incident_id, incident_alerts)

    def _enrich_incident_with_alerts(
        self,
        incident: IncidentInfo,
    ) -> None:
        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        try:
            extra_data: IncidentExtraData = self._call_manager(
                self.manager.get_extra_incident_data,
                incident_id,
            )
            if extra_data and extra_data.alerts:
                incident.raw_data["alerts"] = [
                    alert.to_json() for alert in extra_data.alerts
                ]
            else:
                incident.raw_data["alerts"] = []
        except XDRException as e:
            self.logger.error(
                f"Failed to fetch extra data (alerts) for incident {incident_id}. "
                f"Alert sync for this incident will be skipped. Error: {e}"
            )
            incident.raw_data["alerts"] = []

    def _sync_secops_case_to_incident(
        self,
        case: CaseDetails,
        case_id: str,
        incident: IncidentInfo,
    ) -> None:
        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        self._sync_case_comments_to_xdr(case_id, incident_id)

        if self._sync_case_status_to_xdr(case, case_id, incident, incident_id):
            self.logger.info(
                f"Successfully synced status from SecOps case {case_id} to XDR "
                f"incident {incident_id}."
            )
            self._remove_synced_entries(
                synced_list=[(case_id, incident_id)],
            )

    def _sync_case_status_to_xdr(
        self,
        case: CaseDetails,
        case_id: str,
        incident: IncidentInfo,
        incident_id: str,
    ) -> bool:
        is_xdr_incident_open: bool = (
            incident.raw_data.get("status") not in constants.XDR_RESOLVED_STATUSES
        )
        closure_reason: str | None = self._get_secops_closure_reason(
            case,
            case_id,
            incident_id,
        )

        if closure_reason and is_xdr_incident_open:
            closure_comment: str | None = self._get_secops_closure_comment(
                case_id,
                incident_id,
            )
            return self._update_xdr_incident_with_closure_details(
                incident_id,
                closure_reason,
                closure_comment,
            )

        return False

    def _update_xdr_incident_with_closure_details(
        self,
        incident_id: str,
        reason: str,
        comment: str | None,
    ) -> bool:
        try:
            status, resolve_comment = self._get_xdr_closure_details(reason, comment)
            self._call_manager(
                self.manager.update_an_incident,
                incident_id=incident_id,
                status=status,
                resolve_comment=resolve_comment,
            )
            self.logger.info(
                f"Successfully closed XDR incident {incident_id} with "
                f"status '{status}'."
            )
            return True
        except XDRException as e:
            self.logger.info(
                f"Failed to update incident status for {incident_id}. Error: {e}"
            )
            return False

    def _get_secops_closure_reason(
        self,
        case: CaseDetails,
        case_id: str,
        incident_id: str,
    ) -> str | None:
        if case.status == CaseDataStatus.CLOSED:
            return self.soar_job.get_case_closure_details([str(case_id)])[0].get(
                "reason"
            )

        return self._find_closed_alert_reason(case, incident_id)

    def _find_closed_alert_reason(
        self,
        case: CaseDetails,
        incident_id: str,
    ) -> str | None:
        alert_details: AlertCard | None = next(
            (
                alert
                for alert in case.alerts
                if utils.get_incident_id_from_alert(self.soar_job, alert) == incident_id
            ),
            None,
        )

        is_alert_closed_in_multi_alert_case: bool = (
            alert_details
            and alert_details.status == constants.ALERT_CLOSE_STATUS
            and len(case.alerts) > 1
        )

        if is_alert_closed_in_multi_alert_case:
            try:
                return alert_details.closure_details.get("reason")
            except AttributeError:
                self.logger.error(
                    f"Alert {alert_details.identifier} is closed but "
                    "closureDetails is missing."
                )

        return None

    def _get_secops_closure_comment(
        self,
        case_id: str,
        incident_id: str,
    ) -> str | None:
        try:
            fresh_case_details: CaseDetails = get_case_overview_details(
                self.soar_job,
                case_id,
            )
            case_details_json: SingleJson = fresh_case_details.to_json()
            return self._find_comment_in_alert_cards(
                case_details_json,
                incident_id,
                case_id,
            )
        except (XDRException, JSONDecodeError) as e:
            self.logger.error(
                f"Failed to get or parse case overview for {case_id}. Error: {e}"
            )
            return None

    def _find_comment_in_alert_cards(
        self,
        case_json: SingleJson,
        incident_id: str,
        case_id: str,
    ) -> str | None:
        for alert_card_json in case_json.get("alertCards", []):
            comment: str | None = self._get_comment_from_alert_card(
                alert_card_json,
                incident_id,
                case_id,
            )
            if comment:
                return comment
        self.logger.info(
            f"Could not find a closure comment for incident {incident_id} in case "
            f"{case_id}."
        )
        return None

    def _get_comment_from_alert_card(
        self,
        alert_card_json: SingleJson,
        incident_id: str,
        case_id: str,
    ) -> str | None:
        try:
            alert_card_obj: AlertCard = AlertCard.from_json(alert_card_json)

            extracted_incident_id: str | None = utils.get_incident_id_from_alert(
                self.soar_job,
                alert_card_obj,
            )

            if extracted_incident_id == incident_id:
                closure_details: SingleJson | None = alert_card_json.get(
                    "closureDetails",
                )
                if closure_details and constants.XDR_COMMENT in closure_details:
                    self.logger.info(
                        "Found closure comment for alert matching incident "
                        f"{incident_id}."
                    )
                    return closure_details.get(constants.XDR_COMMENT)

        except XDRException as e:
            self.logger.error(
                "Failed to process alert card in case "
                f"{case_id} while searching for a comment. Error: {e}"
            )

        return None

    def _get_xdr_closure_details(
        self,
        case_closure_reason: str,
        case_closure_comment: str | None,
    ) -> tuple[str, str]:
        status: str = self._map_secops_reason_to_xdr_status(case_closure_reason)
        comment: str = self._build_xdr_closure_comment(
            case_closure_comment,
            case_closure_reason,
        )
        return status, comment

    def _map_secops_reason_to_xdr_status(
        self,
        reason: str,
    ) -> str:
        if reason == constants.REASON_MALICIOUS:
            return constants.XDR_STATUS_RESOLVED_TRUE_POSITIVE
        if reason == constants.REASON_NOT_MALICIOUS:
            return constants.XDR_STATUS_RESOLVED_FALSE_POSITIVE

        self.logger.info(
            "Could not find a XDR closure mapping for Google SecOps "
            f"reason: '{reason}'. Defaulting to 'Resolved - Other'."
        )
        return constants.XDR_STATUS_RESOLVED_OTHER

    def _build_xdr_closure_comment(
        self,
        comment: str | None,
        reason: str,
    ) -> str:
        if comment:
            return comment

        if reason == constants.REASON_MALICIOUS:
            return "Closed from Google SecOps: Malicious"
        if reason == constants.REASON_NOT_MALICIOUS:
            return "Closed from Google SecOps: Not Malicious"

        return f"Closed from Google SecOps: {reason}"

    def _sync_case_comments_to_xdr(
        self,
        case_id: str,
        incident_id: str,
    ) -> None:
        try:
            new_comments_to_sync: list[str] = self._get_new_secops_comments_for_xdr(
                case_id,
            )

            if not new_comments_to_sync:
                return

            for comment in new_comments_to_sync:
                self._call_manager(
                    self.manager.add_comment_to_incident,
                    incident_id,
                    comment,
                )

            self.logger.info(
                "Successfully synced comments from SecOps to XDR "
                f"incident {incident_id}."
            )

        except XDRException as e:
            self.logger.info(
                "Failed to sync comments from Google SecOps for case "
                f"{case_id}. Error: {e}"
            )

    def _get_new_secops_comments_for_xdr(
        self,
        case_id: str,
    ) -> list[str]:
        secops_comments: list[SingleJson] = self.soar_job.fetch_case_comments(
            case_id=case_id,
            time_filter_type=constants.COMMENTS_MODIFICATION_TIME_FILTER,
            from_timestamp=self.last_run_timestamp_ms,
        )

        if not secops_comments:
            return []

        return [
            f"{constants.SECOPS_COMMENT_PREFIX}{comment['comment']}"
            for comment in secops_comments
            if self._is_valid_secops_comment(comment)
        ]

    def _is_valid_secops_comment(
        self,
        comment: SingleJson,
    ) -> bool:
        content: str = comment.get(constants.XDR_COMMENT, "").strip()
        return bool(content) and not content.startswith(constants.XDR_COMMENT_PREFIX)

    def _sync_case_owner_to_xdr(
        self,
        case: CaseDetails,
        incident: IncidentInfo,
    ) -> None:
        user_mapping_json: str = self.params.user_mapping_json
        if not user_mapping_json:
            self.logger.info("User Mapping JSON is empty. Skipping user sync.")
            return

        if case.assigned_user == "Unassigned":
            self.logger.info(
                f"Case {case.id_} is unassigned. Skipping user sync for XDR "
                f"incident {str(incident.raw_data.get('incident_id'))}."
            )
            return

        try:
            user_mapping: dict[str, str] = json.loads(user_mapping_json)
            self._perform_xdr_owner_update(case, incident, user_mapping)
        except (JSONDecodeError, TypeError) as e:
            self.logger.error(f"Failed to parse User Mapping JSON. Error: {e}")

    def _perform_xdr_owner_update(
        self,
        case: CaseDetails,
        incident: IncidentInfo,
        user_mapping: dict[str, str],
    ) -> None:
        secops_user_identifier: str = case.assigned_user
        xdr_username: str | None = self._get_xdr_username_from_mapping(
            secops_user_identifier,
            user_mapping,
            str(incident.raw_data.get(constants.XDR_INC_ID)),
        )

        if xdr_username:
            self._update_xdr_incident_owner(incident, xdr_username)

    def _get_xdr_username_from_mapping(
        self,
        secops_user_identifier: str,
        user_mapping: dict[str, str],
        incident_id: str,
    ) -> str | None:
        if not secops_user_identifier:
            self.logger.info("Assigned user for case is empty. Skipping user sync.")
            return None

        xdr_username: str | None = user_mapping.get(secops_user_identifier)

        if not xdr_username:
            self.logger.info(
                f"No mapping found for SecOps user '{secops_user_identifier}'. "
                f"Skipping user sync for XDR incident {incident_id}."
            )
            return None

        return xdr_username

    def _update_xdr_incident_owner(
        self,
        incident: IncidentInfo,
        xdr_username: str,
    ) -> None:
        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        try:
            if incident.raw_data.get("assigned_user_mail") != xdr_username:
                self._call_manager(
                    self.manager.update_an_incident,
                    incident_id=incident_id,
                    assigned_user=xdr_username,
                )
                self.logger.info(
                    f"Successfully synced assignee to XDR incident {incident_id} "
                    f"as {xdr_username}."
                )
        except XDRException as e:
            self.logger.error(
                f"Failed to sync assignee for XDR incident {incident_id}. Error: {e}"
            )

    def _save_xdr_alerts_to_context(
        self,
        case: CaseDetails,
        incident_id: str,
        xdr_alerts: list[SingleJson],
    ) -> None:
        if not xdr_alerts:
            self.logger.info(f"No alerts found for XDR incident {incident_id} to sync.")
            return

        try:
            alert_identifier: str | None = self._find_alert_identifier(
                case,
                incident_id,
            )

            if not alert_identifier:
                self.logger.info(
                    "Could not find a matching SecOps alert for XDR incident "
                    f"{incident_id}. Skipping alert context update."
                )
                return

            self.soar_job.set_context_property(
                context_type=constants.ENTITY_TYPE,
                identifier=alert_identifier,
                property_key=constants.XDR_ALERTS_CONTEXT_KEY,
                property_value=json.dumps(xdr_alerts),
            )
            self.logger.info(
                f"Successfully saved alert context for XDR incident {incident_id} "
                f"to SecOps alert {alert_identifier} in case {case.id_}."
            )

        except XDRException as e:
            self.logger.error(
                f"Failed to save XDR alerts to context for incident {incident_id}. "
                f"Error: {e}"
            )

    def _build_incident_to_case_map(self) -> SingleJson:
        incident_ids_to_case_map: SingleJson = {}

        for case_id, incident_ids in self.processed_items.items():
            if self.is_timeout_reached():
                raise TimeoutIsApproachingError
            try:
                case: CaseDetails = get_case_overview_details(self.soar_job, case_id)
                for incident_id in incident_ids:
                    incident_ids_to_case_map[incident_id] = {
                        "case_id": case_id,
                        "case": case,
                    }
            except (XDRException, JSONDecodeError) as e:
                self.logger.error(
                    f"Failed to parse details for case {case_id} during sync from "
                    f"XDR, likely due to an empty API response. Skipping. Error: {e}"
                )

        return incident_ids_to_case_map

    def _fetch_and_process_xdr_incidents(
        self,
        incident_ids_to_case_map: dict[str, SingleJson],
    ) -> None:
        unique_incident_ids: list[str] = list(incident_ids_to_case_map.keys())

        try:
            modified_incidents: list[
                IncidentInfo
            ] = self._fetch_modified_xdr_incidents(
                unique_incident_ids,
            )

            for incident in modified_incidents:
                incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
                related_case_data: SingleJson | None = incident_ids_to_case_map.get(
                    incident_id
                )
                if related_case_data:
                    case: CaseDetails = related_case_data["case"]
                    case_id: str = related_case_data["case_id"]
                    self._process_xdr_incident(incident, case, case_id)

        except XDRException as e:
            if constants.MISSING_PERMISSIONS_ERROR.lower() in str(e).lower():
                self.logger.error(f"Failed to fetch incidents from XDR. Error: {e}")
                raise
            raise e

    def _fetch_modified_xdr_incidents(
        self,
        incident_ids: list[str],
    ) -> list[IncidentInfo]:
        if not incident_ids:
            self.logger.info("No XDR incident IDs found for synchronization.")
            return []

        modification_filter: enum.Enum = enum.Enum("Filter", {"gte": "gte"})

        return self._call_manager(
            self.manager.get_incidents,
            incident_id_list=incident_ids,
            modification_time=self.last_run_timestamp_ms,
            modification_filter_enum=modification_filter.gte,
            search_to=constants.INCIDENTS_LIMIT,
        )

    def _process_xdr_incident(
        self,
        incident: IncidentInfo,
        case: CaseDetails,
        case_id: str,
    ) -> None:
        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        try:
            is_closed: bool = self._close_secops_case_or_alert_if_incident_resolved(
                incident,
                case,
                case_id,
            )
            if is_closed:
                self._remove_synced_entries(
                    synced_list=[(case_id, incident_id)],
                )

            self._sync_incident_comments_to_secops(incident, case, case_id)

        except XDRException as e:
            self.logger.info(
                f"Failed to process XDR incident {incident_id} "
                f"for sync to SecOps. Error: {e}"
            )

    def _remove_synced_entries(
        self,
        synced_list: list[tuple],
    ) -> None:
        for case_id, alert_id in synced_list:
            case_id = str(case_id)
            if alert_id in self.processed_items[case_id]:
                self.processed_items[case_id].remove(alert_id)
                if not self.processed_items[case_id]:
                    del self.processed_items[case_id]

    def _should_close_secops_entity(
        self,
        incident: IncidentInfo,
        case: CaseDetails,
    ) -> bool:
        is_incident_resolved: bool = (
            incident.raw_data.get("status") in constants.XDR_RESOLVED_STATUSES
        )
        is_case_open: bool = case.status == CaseDataStatus.OPENED

        return is_incident_resolved and is_case_open

    def _close_secops_case_or_alert_if_incident_resolved(
        self,
        incident: IncidentInfo,
        case: CaseDetails,
        case_id: str,
    ) -> bool:
        if not self._should_close_secops_entity(incident, case):
            return False

        incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))
        alert_identifier: str | None = self._find_alert_identifier(case, incident_id)

        if not alert_identifier:
            self.logger.info(
                "Could not find a matching alert identifier for XDR "
                f"incident {incident_id}. Skipping closure."
            )
            return False

        return self._attempt_closure_with_fallback(incident, alert_identifier, case_id)

    def _attempt_closure_with_fallback(
        self,
        incident: IncidentInfo,
        alert_identifier: str,
        case_id: str,
    ) -> bool:
        (
            primary_reason,
            primary_root_cause,
            fallback_reason,
            fallback_root_cause,
        ) = self._map_xdr_status_to_closure_reasons(incident.raw_data.get("status"))

        is_primary_closure_successful, response = self._handle_primary_closure(
            incident,
            alert_identifier,
            case_id,
            primary_reason,
            primary_root_cause,
        )

        if is_primary_closure_successful:
            return True

        return self._handle_fallback_closure(
            incident,
            alert_identifier,
            case_id,
            fallback_reason,
            fallback_root_cause,
            primary_reason,
            primary_root_cause,
            response,
        )

    def _handle_primary_closure(
        self,
        incident: IncidentInfo,
        alert_identifier: str,
        case_id: str,
        reason: str,
        root_cause: str,
    ) -> tuple[bool, SingleJson]:
        response: SingleJson = self._attempt_closure(
            reason=reason,
            root_cause=root_cause,
            alert_identifier=alert_identifier,
            case_id=case_id,
            closure_comment=incident.raw_data.get("resolve_comment") or "",
            incident_id=str(incident.raw_data.get(constants.XDR_INC_ID)),
        )

        if not (response and response.get("errorMessage")):
            self.logger.info(
                f"Successfully closed alert {alert_identifier} in case {case_id}."
            )
            return True, response

        return False, response

    def _handle_fallback_closure(
        self,
        incident: IncidentInfo,
        alert_identifier: str,
        case_id: str,
        fallback_reason: str | None,
        fallback_root_cause: str | None,
        primary_reason: str,
        primary_root_cause: str,
        original_response: SingleJson,
    ) -> bool:
        if not (fallback_reason and fallback_root_cause):
            self.logger.error(
                f"Failed to close alert {alert_identifier} in case {case_id}."
                f"Original error: {original_response.get('errorMessage')}"
            )
            return False

        self.logger.info(
            "Failed to close with primary reason/root cause"
            f" {primary_reason}/{primary_root_cause}. Falling back to"
            f" {fallback_reason}/{fallback_root_cause}."
        )

        is_fallback_closure_successful, response = self._handle_primary_closure(
            incident,
            alert_identifier,
            case_id,
            fallback_reason,
            fallback_root_cause,
        )

        if not is_fallback_closure_successful:
            self.logger.error(
                f"Failed to close alert {alert_identifier} in case {case_id}."
                f"Original error: {response.get('errorMessage')}"
            )

        return is_fallback_closure_successful

    def _map_xdr_status_to_closure_reasons(
        self,
        incident_status: str,
    ) -> tuple[str, str, str | None, str | None]:
        default_reasons: tuple[str, str, str | None, str | None] = (
            constants.REASON_INCONCLUSIVE,
            CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
            None,
            None,
        )
        return constants.XDR_STATUS_TO_CLOSURE_REASONS_MAP.get(
            incident_status,
            default_reasons,
        )

    def _attempt_closure(
        self,
        reason: str,
        root_cause: str,
        alert_identifier: str,
        case_id: str,
        closure_comment: str,
        incident_id: str,
    ) -> SingleJson:
        close_comment_str: str = (
            f"{closure_comment} Closed automatically due to Palo Alto Cortex XDR "
            f"incident status change. XDR Incident ID: {incident_id}. "
            f"Reason: {reason}"
        )
        try:
            response: SingleJson = self.soar_job.close_alert(
                root_cause=root_cause,
                comment=close_comment_str,
                reason=reason,
                case_id=case_id,
                alert_id=alert_identifier,
            )
            return response
        except XDRException as e:
            self.logger.error(f"Failed to close alert with {reason}/{root_cause}: {e}")
            return {"errorMessage": str(e)}

    def _sync_incident_comments_to_secops(
        self,
        incident: IncidentInfo,
        case: CaseDetails,
        case_id: str,
    ) -> None:
        try:
            notes_content: str | None = incident.raw_data.get("notes")
            incident_id: str = str(incident.raw_data.get(constants.XDR_INC_ID))

            if (
                not notes_content
                or not isinstance(notes_content, str)
                or not self._is_valid_xdr_comment(notes_content)
            ):
                return

            full_comment: str = (
                f"Palo Alto XDR Incident {incident_id}: "
                f"{utils.strip_html_tags(notes_content)}"
            )

            self._add_xdr_comment_to_secops(case, case_id, incident_id, full_comment)

        except XDRException as e:
            incident_id = str(incident.raw_data.get(constants.XDR_INC_ID))
            self.logger.info(
                "Failed to sync comments from XDR for incident "
                f"{incident_id}. Error: {e}"
            )

    def _add_xdr_comment_to_secops(
        self,
        case: CaseDetails,
        case_id: str,
        incident_id: str,
        comment: str,
    ) -> None:
        try:
            existing_comments: set[str] = {
                existing_comment.get(constants.XDR_COMMENT, "")
                for existing_comment in self.soar_job.fetch_case_comments(
                    case_id=case_id,
                )
            }

            if comment not in existing_comments:
                alert_identifier: str | None = self._find_alert_identifier(
                    case,
                    incident_id,
                )
                self.soar_job.add_comment(
                    case_id=case_id,
                    comment=comment,
                    alert_identifier=alert_identifier,
                )
                self.logger.info(
                    "Successfully synced new comment from XDR incident "
                    f"{incident_id} to SecOps case {case_id}."
                )
        except XDRException as e:
            self.logger.error(
                f"Could not fetch existing comments for case {case_id}. "
                f"Aborting comment sync. Error: {e}"
            )

    def _is_valid_xdr_comment(
        self,
        comment: str,
    ) -> bool:
        clean_comment: str = utils.strip_html_tags(comment)
        return not clean_comment.startswith(constants.SECOPS_COMMENT_PREFIX)

    def modified_synced_case_ids_by_product(
        self,
        _incident_ids: list[str],
    ) -> list[tuple[int, int]]:
        """Get case ids with modified timestamp from product system."""
        return []

    def _fetch_case_ids(
        self,
        ids: list[str] | None = None,
    ) -> CaseInfoList:
        candidate_case_tuples: CaseInfoList = self._get_case_ids_by_timestamp(ids)

        if not candidate_case_tuples:
            self.logger.info("No new/modified cases found in the given time range.")
            return []

        if ids is not None:
            log_message = (
                f"Found {len(candidate_case_tuples)} new/modified case IDs from "
                "previously processed items: "
            )
        else:
            log_message = (
                f"Found {len(candidate_case_tuples)} new/modified case IDs: "
            )

        self.logger.info(
            f"{log_message}{[case_id for case_id, _ in candidate_case_tuples]}"
        )

        return candidate_case_tuples

    def _get_case_ids_by_timestamp(
        self,
        ids: list[str] | None = None,
    ) -> CaseInfoList:
        start_time_ms: int = (
            convert_datetime_to_unix_time(self.last_processed_case_timestamp)
            + constants.INCREMENT_CASE_UPDATED_TIME_BY_MS
        )
        time_diff_ms: float = unix_now() - start_time_ms
        ms_per_day: float = 86400000.0
        duration_days: float = time_diff_ms / ms_per_day

        time_range_filter_value: int = max(1, math.ceil(duration_days))
        cases: list[dict] = get_cases_by_timestamp_filter(
            chronicle_soar=self.soar_job,
            start_time=start_time_ms,
            end_time=unix_now(),
            time_range_filter=time_range_filter_value,
            environments=[self.params.environment_name],
            case_ids=[int(case_id) for case_id in ids] if ids is not None else None,
        )
        if not self.tags:
            filtered_case_ids: CaseInfoList = []
            for case in cases:
                if case.get("id"):
                    filtered_case_ids.append((str(case["id"]), case["updateTime"]))
            return filtered_case_ids

        return self._filter_cases_by_tags(cases)

    def _filter_cases_by_tags(
        self,
        cases: list[dict[str, any]],
    ) -> CaseInfoList:
        filtered_case_ids: CaseInfoList = []

        for case in cases:
            case_tags_display_names: list[str] = [
                tag_dict.get("displayName")
                for tag_dict in case.get("tags", [])
                if tag_dict and tag_dict.get("displayName")
            ]

            case_id: str | None = case.get("id")
            if all(tag in case_tags_display_names for tag in self.tags) and case_id:
                filtered_case_ids.append((str(case_id), case["updateTime"]))

        return filtered_case_ids

    def _extract_product_ids_from_case(
        self,
        case_details: CaseDetails,
    ) -> SyncItem:
        incident_ids: list[str] = []
        for alert in case_details.alerts:
            if alert.status != constants.ALERT_CLOSE_STATUS:
                ticket_id: str | None = utils.get_incident_id_from_alert(
                    self.soar_job,
                    alert,
                )
                if ticket_id and utils.is_valid_alert_id(ticket_id):
                    incident_ids.append(ticket_id)

        case_id: str = str(case_details.id_)
        existing_tracked_ids: set[str] = set(self.processed_items.get(case_id, []))
        final_ids: set[str] = existing_tracked_ids.union(set(incident_ids))

        return sorted(list(final_ids))

    def _find_alert_identifier(
        self,
        case: CaseDetails,
        incident_id: str,
    ) -> str | None:
        for alert in case.alerts:
            extracted_incident_id: str | None = utils.get_incident_id_from_alert(
                self.soar_job, alert
            )
            if extracted_incident_id == incident_id:
                return alert.identifier

        return None

    def _read_state(self) -> SyncData:
        context_str: str = self.soar_job.get_job_context_property(
            self.name_id,
            self.context_identifier,
        )
        if context_str:
            return json.loads(context_str)

        return {}

    def _write_state(self, updated_items: SyncData) -> None:
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=self.context_identifier,
            property_value=json.dumps(updated_items),
        )

    def is_timeout_reached(self) -> bool:
        """Check if the job is about to reach its timeout.

        Returns:
            bool: True if the timeout is approaching, False otherwise.
        """
        if self._job_start_time == -1:
            return False

        time_passed_ms: int = unix_now() - self._job_start_time
        return time_passed_ms >= self.timeout_in_milliseconds

    def _call_manager(self, func, *args, **kwargs):
        """
        Wrapper to call a manager method with auth-retry logic.
        Catches an authorization error, re-initializes the API client, and retries the
        call once.
        """
        try:
            return func(*args, **kwargs)
        except XDRException as e:
            if "unauthorized" in str(e).lower() or "401" in str(e):
                self.logger.info(
                    f"Authorization error during call to '{func.__name__}'"
                    ". Re-authenticating and retrying."
                )
                self._init_api_clients()
                new_func = getattr(self.manager, func.__name__)
                return new_func(*args, **kwargs)
            raise


def main() -> NoReturn:
    SyncIncidents().start()


if __name__ == "__main__":
    main()
