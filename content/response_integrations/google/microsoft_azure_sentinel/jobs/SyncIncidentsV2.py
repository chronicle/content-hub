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

from collections.abc import Callable
from collections import defaultdict
from contextlib import suppress
import datetime
import json
from typing import TYPE_CHECKING

from requests.exceptions import ConnectionError as RequestsConnectionError

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, convert_unixtime_to_datetime

from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import (
    JobCase,
    CaseTagsData,
    SyncMetadata,
    JobStatusResult
)
from TIPCommon.data_models import AlertCard, CaseDataStatus

from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core.exceptions import MicrosoftAzureSentinelBadRequestError
from ..core import constants
from ..core.datamodels import Incident


if TYPE_CHECKING:
    from typing import NoReturn, Any


class SyncIncidentsV2(BaseSyncJob[MicrosoftAzureSentinelManager]):
    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_INCIDENTS_V2_JOB_NAME,
            context_identifier=constants.SYNC_INCIDENTS_V2_CONTEXT_IDENTIFIER,
            tags_identifiers=[constants.SECOPS_CASE_TAG],
        )
        self.sync_limit = constants.CASES_SYNC_LIMIT
        self.manager = MicrosoftAzureSentinelManager

    def _init_api_clients(self) -> None:
        self.manager = MicrosoftAzureSentinelManager(
            api_root=self.params.management_api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            tenant_id=self.params.azure_active_directory_id,
            workspace_id=self.params.azure_sentinel_workspace_name,
            resource=self.params.azure_resource_group,
            subscription_id=self.params.azure_subscription_id,
            login_url=self.params.oauth2_login_endpoint_url,
            verify_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
            siemplify=self.soar_job,
        )

    def modified_synced_case_ids_by_product(
        self,
        incident_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Fetches modified incidents from Microsoft Sentinel and maps them to
        SecOps case IDs along with their modification timestamps.
        Args:
            incident_ids (list[str]): List of Microsoft Sentinel incident ids.

        Returns:
            list[tuple[str, int]]: List of tuples containing SecOps case ID and
            modification timestamp in milliseconds.
        """
        product_to_case = self.incident_ids_to_case_map_builder()
        incident_numbers = self._extract_incident_numbers(incident_ids)
        modified_incidents = self._fetch_modified_incidents(incident_numbers)

        return self._map_incidents_to_cases(
            modified_incidents,
            product_to_case,
            sorted_modified_ids,
        )

    def _extract_incident_numbers(self, incident_ids: list[str]) -> list[str]:
        return [
            incident_id.split(":")[1] for incident_id in incident_ids if incident_id
        ]

    def _fetch_modified_incidents(self, incident_numbers: list[str]) -> list[Incident]:
        incidents = []
        for i in range(0, len(incident_numbers), constants.BATCH_SIZE):
            batch = incident_numbers[i : i + constants.BATCH_SIZE]
            incidents.extend(
                self._retry(
                    self.manager.get_incidents_by_numbers_and_timestamp,
                    batch,
                    convert_unixtime_to_datetime(self.last_run_time),
                )
            )
        return incidents

    def _map_incidents_to_cases(
        self,
        incidents,
        product_to_case: dict[str, str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        results = []

        for incident in incidents:
            incident_id = f"{incident.name}:{incident.properties.incident_number}"
            case_id = product_to_case.get(incident_id)
            if not case_id:
                self.logger.info(
                    f"Skipping incident sync for Sentinel Incident ID {incident_id} "
                    "as no matching SecOps case/alert ID was found in the map."
                )
                continue

            modified_time_ms = self._get_incident_modified_time_ms(incident)
            case_time_ms = next(
                (t for cid, t in sorted_modified_ids if cid == case_id),
                0,
            )
            results.append((case_id, max(modified_time_ms, case_time_ms)))

        return results

    def _get_incident_modified_time_ms(self, incident: Incident) -> int:
        modified_time = datetime.datetime.fromisoformat(
            incident.properties.last_modified_time_utc.replace("Z", "+00:00")
        )
        return convert_datetime_to_unix_time(modified_time)

    def incident_ids_to_case_map_builder(self) -> dict[str, str]:
        """Builds a mapping of Microsoft Sentinel incident IDs to SecOps case IDs."""
        product_ids_to_case_map: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids:
                product_ids_to_case_map[product_id] = case_id

        return product_ids_to_case_map

    def is_alert_and_product_closed(
        self,
        job_case: JobCase,
        incident: Incident
    ) -> bool:
        """
        Check if both the case alert and the Microsoft Sentinel incident are closed.
        """
        product_id = incident.name
        alert = next(
            (
                alert
                for alert in job_case.case_detail.alerts
                if alert.ticket_id == product_id
            ),
            None,
        )
        if not alert:
            return False

        alert_closed = alert.status.lower() == constants.CASE_ALERT_CLOSED_STATUS

        product_status = incident.properties.status

        product_closed = (
            product_status.lower() == constants.INCIDENT_CLOSED_STATUS.lower()
        )
        return alert_closed and product_closed

    def _extract_product_ids_from_case(
        self,
        job_case: JobCase,
    ) -> list[str]:
        """
        Extracts Microsoft Sentinel incident IDs from SecOps case alerts
        and fetches their details to build a list of incident IDs.
        """
        incident_ids: list[str] = []
        for alert in job_case.case_detail.alerts:
            properties = json.loads(alert.additional_properties)
            incident_number = properties.get("incidentNumber")
            if not incident_number:
                continue
            incident_id = f"{alert.ticket_id}:{incident_number}"
            incident_ids.append(incident_id)
        return sorted(set(incident_ids))

    def get_product_ids_from_case_alerts(
        self,
        job_case: JobCase
    ) -> dict[str, AlertCard]:
        """Extracts Microsoft Sentinel incident IDs from SecOps case alerts."""
        product_ids_to_alert_mapping = {}
        for alert in job_case.case_detail.alerts:
            additional_properties = json.loads(alert.additional_properties)
            if additional_properties.get("incidentNumber"):
                product_ids_to_alert_mapping[alert.ticket_id] = alert

        return product_ids_to_alert_mapping

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps Microsoft Sentinel incident data to SecOps case alerts."""
        mapping: dict[str, AlertCard] = self.get_product_ids_from_case_alerts(job_case)
        product_ids: list[str] = list(mapping.keys())
        job_case.product_ids_from_secops_alerts = mapping
        product_details: list[Incident] = self._fetch_product_details(product_ids)
        self._enrich_incidents_with_comments(product_details)
        product_alerts: list[Any] = self._fetch_product_alerts(product_ids)

        self._attach_alerts_to_incidents(product_details, product_alerts)
        self._attach_incidents_to_case(job_case, product_details)
        self._save_incident_alerts_to_db(job_case, product_alerts)
        self._populate_alert_metadata(job_case, product_details)
        self.remove_synced_data_from_db(job_case, product_details)

    def _fetch_product_details(self, product_ids: list[str]) -> list[Incident]:
        """Fetches incident details from Microsoft Sentinel."""
        product_ids = list(set(product_ids))
        return self._retry(self.manager.get_incidents_v2_details, product_ids)

    def _enrich_incidents_with_comments(self, incidents: list[Incident]) -> None:
        """Fetches and attaches comments to incidents."""
        incident_names: list[str] = list(set(incident.name for incident in incidents))
        comments = self._retry(
            self.manager.get_incidents_v2_comments,
            incident_names,
            convert_unixtime_to_datetime(self.last_run_time),
        )
        for incident in incidents:
            incident.add_comments(comments)

    def _fetch_product_alerts(self, product_ids: list[str]) -> list[Any]:
        """Fetches alerts for the given incident IDs."""
        product_ids = list(set(product_ids))
        return self._retry(self.manager.get_incidents_v2_alerts, product_ids)

    def _attach_alerts_to_incidents(
        self,
        incidents: list[Incident],
        alerts: list[Any]
    ) -> None:
        """Attaches alerts to their respective incidents."""
        for incident in incidents:
            incident.add_alerts(alerts)

    def _attach_incidents_to_case(
        self,
        job_case: JobCase,
        incidents: list[Incident]
    ) -> None:
        """Attaches incidents to the SecOps case."""
        for incident in incidents:
            job_case.add_product_incident(incident, product_key="name")

    def _populate_alert_metadata(
        self,
        job_case: JobCase,
        incidents: list[Incident]
    ) -> None:
        """Populates alert metadata for each alert in the case."""
        for alert in job_case.case_detail.alerts:
            for incident in incidents:
                if incident.name == alert.ticket_id:
                    job_case.alert_metadata[alert.identifier] = SyncMetadata(
                        status=incident.properties.status,
                        severity=incident.properties.severity,
                        assignee=incident.properties.owner.assigned_to,
                        incident_id=incident.name,
                        incident_number=incident.properties.incident_number,
                        closure_reason=incident.properties.classification,
                        closure_comment=incident.properties.classificationComment,
                    )
                    break

    def _group_incident_alerts_by_incident_name(
        self,
        product_alerts: list[Any]
    ) -> dict[str, list]:
        """
        Groups incident alerts by their incident name using product alerts.
        """
        incident_alerts_by_incident = defaultdict(list)
        for alert in product_alerts:
            incident_name = getattr(alert, "incident_name", "")
            incident_name = incident_name.replace("get-incident-alerts-", "")
            if incident_name:
                incident_alerts_by_incident[incident_name].append(alert.to_json())
        return incident_alerts_by_incident

    def _save_incident_alerts_to_db(
        self,
        job_case: JobCase,
        product_alerts: list[Any]
    ) -> None:
        """
        Saves incident alerts for each incident to the SecOps context.
        """
        incident_alerts_by_incident = self._group_incident_alerts_by_incident_name(
            product_alerts
        )
        for incident_name, incident_alerts in incident_alerts_by_incident.items():
            try:
                json_encoded_incident_alerts = json.dumps(incident_alerts)
            except (TypeError, ValueError) as e:
                self.logger.error(
                    "Failed to JSON encode incident alerts for incident "
                    f"{incident_name}. Error: {e}"
                )
                continue

            secops_alert_identifier = None
            for alert in job_case.case_detail.alerts:
                with suppress(AttributeError):
                    if alert.incident.name == incident_name:
                        secops_alert_identifier = alert.identifier
                        break

            if secops_alert_identifier:
                self.soar_job.set_context_property(
                    context_type=constants.ENTITY_TYPE,
                    identifier=secops_alert_identifier,
                    property_key=constants.SENTINEL_ALERTS_CONTEXT_KEY,
                    property_value=json_encoded_incident_alerts,
                )

    def sync_status(self, job_case: JobCase) -> None:
        """Handles bi-directional status synchronization."""
        res = job_case.get_status_to_sync(constants.INCIDENT_CLOSED_STATUS)
        self._sync_product_status_to_case(res, job_case)
        self._sync_case_status_to_product(res, job_case)

    def _sync_product_status_to_case(
        self,
        res: JobStatusResult,
        job_case: JobCase
    ) -> None:
        """Syncs product status to case."""
        for alert, meta in res.alerts_to_close_in_soar:
            reason, root_cause = self._get_secops_closure_details(meta.closure_reason)
            if meta.closure_comment:
                comment = meta.closure_comment
            else:
                comment = (
                    f"{constants.SENTINEL_INCIDENT_COMMENT_PREFIX}"
                    f"{meta.incident_number}: Incident was closed."
                )
            self.sync_product_status_to_case(
                case_id=job_case.case_detail.id_,
                alert_id=alert.identifier,
                reason=reason,
                root_cause=root_cause,
                comment=comment,
            )
            self._remove_synced_entries(
                [
                    (
                        job_case.case_detail.id_,
                        f"{meta.incident_id}:{meta.incident_number}",
                    )
                ]
            )

    def _sync_case_status_to_product(
        self,
        res: JobStatusResult,
        job_case: JobCase
    ) -> None:
        """Syncs case status to product."""
        if res.incidents_to_close_in_product:
            for req in res.incidents_to_close_in_product:
                if req["is_case_closed"]:
                    closure_reason = self.soar_job.get_case_closure_details(
                        [job_case.case_detail.id_]
                    )[0].get("reason", "")
                else:
                    closure_reason = req["reason"]
                classification = self._get_sentinel_closure_mapping(closure_reason)
                comment = self.get_secops_closure_comment(job_case, req)
                incident_number = req["meta"].incident_number
                incident_id = req["meta"].incident_id
                self.manager.update_incident(
                    incident_number=incident_number,
                    status=constants.INCIDENT_CLOSED_STATUS,
                    close_reason=classification,
                    closing_comment=comment,
                )
                self.logger.info(f"Successfully updated incident {incident_number}.")
                self._remove_synced_entries(
                    [
                        (
                            job_case.case_detail.id_,
                            f"{incident_id}:{incident_number}",
                        )
                    ]
                )

    def sync_severity(self, job_case: JobCase) -> None:
        """Sentinel -> SecOps: Updates alert priority."""
        res = job_case.get_severity_to_sync(constants.SENTINEL_TO_SECOPS_SEVERITY_MAP)
        for alert, new_priority in res.updates:
            if alert.status.lower() == "close":
                return
            self.sync_severity_to_case(
                case_id=job_case.case_detail.id_,
                alert_identifier=alert.identifier,
                alert_name=alert.name,
                new_priority=new_priority,
            )

    def sync_assignee(self, job_case: JobCase) -> None:
        """Sentinel -> SecOps: Assigns case to matching user."""
        if (
            not self.params.sync_assignee
            or job_case.case_detail.status == CaseDataStatus.CLOSED
        ):
            return

        res = self.get_assignee_to_sync(job_case)
        if res.target_user:
            current_case_user = self.get_secops_assignee(job_case)
            secops_assignee = (
                current_case_user.raw_data.get("userFullName")
                if current_case_user and current_case_user.raw_data
                else ""
            )
            if secops_assignee != res.target_user.get("userFullName"):
                self.sync_assignee_to_case(
                    user_display_name=res.target_user.get("displayName"),
                    case_id=job_case.case_detail.id_,
                    alert_id=res.alert.identifier,
                )

    def _get_secops_closure_details(
        self,
        product_classification: str
    ) -> tuple[str, str]:
        """
        Maps Microsoft Sentinel incident classification to SecOps closure reason
        and root cause.
        """
        mapping = {
            "TruePositive": (
                "Malicious",
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            ),
            "FalsePositive": (
                "NotMalicious",
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            ),
        }
        return mapping.get(
            product_classification,
            (
                "Inconclusive",
                CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
            ),
        )

    def _get_sentinel_closure_mapping(self, secops_reason: str) -> str:
        """Maps SecOps closure reason to Microsoft Sentinel incident classification."""
        mapping: dict[str, str] = {
            "Malicious": "True Positive - suspicious activity",
            "NotMalicious": "False Positive - incorrect alert logic",
        }
        closure_details = mapping.get(secops_reason)
        if closure_details:
            return closure_details
        self.logger.warn(
            "Could not find a Sentinel closure mapping for Google SecOps "
            f"reason: '{secops_reason}'. Defaulting to 'Undetermined'."
        )
        return "Undetermined"

    def sync_comments(self, job_case: JobCase) -> None:
        """
        Sync comments between source and target items.
        """
        if job_case.case_detail.status == CaseDataStatus.CLOSED:
            return

        comments_to_sync = self.get_comments_to_sync(
            job_case=job_case,
            product_comment_prefix=constants.SENTINEL_INCIDENT_COMMENT_PREFIX,
            case_comment_prefix=constants.SECOPS_CASE_COMMENT_PREFIX,
            product_comment_key="message",
            product_incident_key="incident_number",
        )

        self.sync_product_comments_to_case(
            case_id=job_case.case_detail.id_,
            comments=comments_to_sync.product_comments_sync_to_case,
        )
        self.sync_case_comments_to_product(
            job_case=job_case,
            comments=comments_to_sync.case_comments_sync_to_product,
        )

    def sync_case_comments_to_product(
        self,
        job_case: JobCase,
        comments: list[str],
    ) -> None:
        """Syncs comments from SecOps case to Microsoft Sentinel incident."""
        for incident in self._get_open_unique_incidents(job_case):
            for block in self._chunk_comments(comments):
                self._push_comment_to_incident(incident, block)

    def _get_open_unique_incidents(self, job_case: JobCase):
        incidents = set()
        for alert in job_case.case_detail.alerts:
            inc = getattr(alert, "incident", None)
            if inc and inc.properties.status != constants.INCIDENT_CLOSED_STATUS:
                incidents.add(inc)
        return incidents

    def _chunk_comments(self, comments: list[str]) -> list[str]:
        blocks, current, length = [], [], constants.DEFAULT_COMMENT_LENGTH
        for comment in comments:
            extra = len(comment) + (1 if current else 0)
            if length + extra > constants.MAX_CHARS:
                blocks.append("\n".join(current))
                current, length = [comment], len(comment)
            else:
                current.append(comment)
                length += extra
        if current:
            blocks.append("\n".join(current))

        return blocks

    def _push_comment_to_incident(self, incident: Incident, text: str) -> None:
        try:
            self.manager.add_comment_to_incident(incident.name, text)
            self.logger.info(
                "Successfully synced comments from secops to sentinel incident "
                f"{incident.incident_number}."
            )
        except MicrosoftAzureSentinelBadRequestError as e:
            if "maximum number of comments" in str(e):
                self.logger.info(
                    f"Incident {incident.incident_number} reached comment limit. "
                    "Skipping."
                )

    def sync_tags(self, job_case: JobCase) -> None:
        """
        Sync tags between source and target items.
        """
        if job_case.case_detail.status == CaseDataStatus.CLOSED:
            return
        incidents, tags_to_update = job_case.get_product_tags_to_sync_to_products(
            product_properties_key="properties", tags_key="labels"
        )

        self.sync_product_tags_to_products(incidents, tags_to_update)

        tags_result = self.get_tags_to_sync(
            job_case,
            product_tag_prefix=constants.SENTINEL_TAG_PREFIX,
            case_tag_prefix=constants.SECOPS_TAG_PREFIX,
            product_properties_key="properties",
            product_tags_key="labels",
        )
        self.sync_product_tags_to_case(
            job_case.case_detail.id_,
            tags_result.product_tags_sync_to_case,
        )
        self.sync_case_tags_to_product(
            job_case=job_case,
            tags=tags_result.case_tags_sync_to_product,
        )

    def sync_product_tags_to_products(
        self,
        incidents: list[Incident],
        tags_to_update: list[str],
    ) -> None:
        """Syncs tags between the Microsoft Sentinel incidents."""
        for incident in incidents:
            self.manager.update_incident_labels(
                incident_number=incident.incident_number,
                labels=tags_to_update,
            )

    def sync_case_tags_to_product(
        self,
        job_case: JobCase,
        tags: CaseTagsData,
    ) -> None:
        """Syncs tags from SecOps case to Microsoft Sentinel incident."""
        if not (tags.tags_to_add or tags.tags_to_remove):
            return
        unique_incidents = set()
        for alert in job_case.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue
            if alert.incident.properties.status == constants.INCIDENT_CLOSED_STATUS:
                continue
            unique_incidents.add(alert.incident.incident_number)

        for incident_number in unique_incidents:
            tags_to_update = (
                set(
                    job_case.product_tags(
                        product_properties_key="properties", tags_key="labels"
                    )
                )
                .union(set(tags.tags_to_add))
                .difference(set(tags.tags_to_remove))
            )
            tags_to_update = [
                {"labelName": tag, "labelType": "User"} for tag in tags_to_update
            ]

            if tags_to_update:
                self.manager.update_incident(
                    incident_number=incident_number,
                    labels=tags_to_update,
                )
                self.logger.info(
                    "Successfully updated tags to Microsoft Sentinel incident "
                    f"{incident_number}."
                )

    def remove_synced_data_from_db(
        self,
        job_case: JobCase,
        product_details: list[Incident]
    ) -> None:
        """
        Removes synced entries from the DB if both the alert
        and the incident are closed.
        """
        for alert in job_case.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue

            matching_product = None
            for product in product_details:
                if product.name == alert.ticket_id:
                    matching_product = product
                    break

            if not matching_product:
                continue

            if self.is_alert_and_product_closed(job_case, matching_product):
                case_id = job_case.case_detail.id_
                incident_id = (
                    f"{matching_product.name}:{matching_product.incident_number}"
                )

                self._remove_synced_entries([(case_id, incident_id)])

    def _retry(self, func: Callable, *args):
        """Helper to retry a function call if a ConnectionError occurs."""
        try:
            return func(*args)
        except RequestsConnectionError as err:
            self.logger.error(err)
            self.logger.error(
                "Connection unexpectedly closed. Reopening the connection."
            )
            self._init_api_clients()
            return func(*args)


def main() -> NoReturn:
    SyncIncidentsV2().start()


if __name__ == "__main__":
    main()
