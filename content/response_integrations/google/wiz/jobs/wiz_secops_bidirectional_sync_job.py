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

import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NoReturn

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import CaseDataStatus

from ..core import action_init, constants
from ..core.api_client import WizApiClient

if TYPE_CHECKING:
    from TIPCommon.data_models import AlertCard

    from ..core.datamodels import Issue


class WizSecopsBidirectionalSyncJob(BaseSyncJob[WizApiClient]):
    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_JOB_SCRIPT_NAME,
            context_identifier=constants.SYNC_JOB_IDENTIFIER,
            tags_identifiers=["Wiz"],
        )
        self.sync_status_enabled: bool = True
        self.sync_comments_enabled: bool = True
        self.sync_product_link_enabled: bool = True
        self.sync_severity_enabled: bool = True
        self.failed_cases: set[str] = set()
        self._escalated_threats: set[tuple[int, str, str]] = set()

    def _init_api_clients(self) -> WizApiClient:
        fields_to_sync: list[str] = [
            f.strip().lower()
            for f in getattr(
                self.params,
                "fields_to_sync",
                "Status, Comments, Product Link, Severity",
            ).split(",")
        ]
        self.sync_status_enabled = "status" in fields_to_sync
        self.sync_comments_enabled = "comments" in fields_to_sync
        self.sync_product_link_enabled = "product link" in fields_to_sync
        self.sync_severity_enabled = "severity" in fields_to_sync

        client: WizApiClient = action_init.create_api_client(self.soar_job)
        return client

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Map Wiz threat details to the SOAR case details.

        Args:
            job_case (JobCase): The SecOps case containing the alerts.

        """
        try:
            self._map_alerts_to_threat_ids(job_case)
            self._fetch_and_add_threats_to_case(job_case)
        except Exception:
            self.logger.exception(
                f"Failed to map product data to case {job_case.case_detail.id_}."
            )
            self.failed_cases.add(job_case.case_detail.id_)

    def _map_alerts_to_threat_ids(self, job_case: JobCase) -> None:
        mapping: dict[str, AlertCard] = {}
        full_mapping: dict[str, list[AlertCard]] = {}
        for alert in job_case.case_detail.alerts:
            threat_id: str | None = self._extract_clean_threat_id(
                self._get_wiz_threat_id(alert)
            )
            if threat_id:
                full_mapping.setdefault(threat_id, []).append(alert)
                if threat_id not in mapping:
                    mapping[threat_id] = alert
        job_case.product_ids_from_secops_alerts = mapping
        self.case_threat_alerts[job_case.case_detail.id_] = full_mapping

    @staticmethod
    def _extract_clean_threat_id(threat_id: str | None) -> str | None:
        if not threat_id:
            return None
        if "_" not in threat_id:
            return threat_id
        last_part: str = threat_id.split("_")[-1]
        if len(last_part) == constants.UUID_LENGTH and "-" in last_part:
            return last_part
        return threat_id

    def _get_wiz_threat_id(self, alert: AlertCard) -> str | None:
        if not alert.additional_properties:
            return None
        try:
            props: dict[str, Any] = json.loads(alert.additional_properties)
            if isinstance(props, dict):
                val: Any = (
                    props.get("security_result_threat_id")
                    or props.get("SourceGroupingIdentifier")
                    or props.get("sourceGroupingIdentifier")
                )
                if val:
                    return str(val)
        except (json.JSONDecodeError, TypeError):
            self.logger.exception("Failed to parse additional_properties.")
        return None

    def _fetch_and_add_threats_to_case(self, job_case: JobCase) -> None:
        threat_ids: list[str] = self._extract_product_ids_from_case(job_case)
        for threat_id in threat_ids:
            self._fetch_and_add_single_threat(job_case, threat_id)

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        threat_ids: list[str] = []
        for alert in job_case.case_detail.alerts:
            threat_id: str | None = self._extract_clean_threat_id(
                self._get_wiz_threat_id(alert)
            )
            if threat_id:
                threat_ids.append(threat_id)
        return sorted(set(threat_ids))

    def _fetch_and_add_single_threat(self, job_case: JobCase, threat_id: str) -> None:
        try:
            threat_issue: Issue = self.api_client.get_issue_details(threat_id)
            job_case.add_product_incident(threat_issue, product_key="issue_id")
            self._register_alert_sync_metadata(job_case, threat_id, threat_issue)
        except Exception:
            self.logger.exception(
                f"Failed to fetch or map Wiz threat {threat_id} details."
            )
            raise

    def _register_alert_sync_metadata(
        self, job_case: JobCase, threat_id: str, threat_issue: Issue
    ) -> None:
        alerts: list[AlertCard] = self.case_threat_alerts.get(
            job_case.case_detail.id_, {}
        ).get(threat_id, [])
        for alert in alerts:
            job_case.alert_metadata[alert.identifier] = SyncMetadata(
                status=threat_issue.status,
                severity=threat_issue.severity,
            )

    @property
    def case_threat_alerts(self) -> dict[int, dict[str, list[AlertCard]]]:
        """The mapped Wiz threats to alert cards dictionary.

        Returns:
            dict[int, dict[str, list[AlertCard]]]: The mapping dictionary.

        """
        if not hasattr(self, "_case_threat_alerts"):
            self._case_threat_alerts = {}
        return self._case_threat_alerts

    def is_alert_and_product_closed(self, job_case: JobCase, product: Issue) -> bool:
        """Check if both the alert and the Wiz threat are closed.

        Args:
            job_case (JobCase): The SecOps case.
            product (Issue): The Wiz incident/issue object.

        Returns:
            bool: True if both the alert and the Wiz threat are closed, False otherwise.

        """
        alerts: list[AlertCard] = self.case_threat_alerts.get(
            job_case.case_detail.id_, {}
        ).get(product.issue_id, [])
        if not alerts:
            alert: AlertCard | None = job_case.product_ids_from_secops_alerts.get(
                product.issue_id
            )
            alerts = [alert] if alert else []
        if not alerts:
            return False
        alerts_closed: bool = all(alert.status.lower() in {"close", "closed"} for alert in alerts)
        product_closed: bool = product.status.upper() in constants.WIZ_CLOSED_STATUSES
        return alerts_closed and product_closed

    def sync_status(self, job_case: JobCase) -> None:
        """Synchronize status between Wiz Threats and SOAR Case/Alerts.

        Args:
            job_case (JobCase): The SecOps case.

        """
        if (
            not self.sync_status_enabled
            or job_case.case_detail.id_ in self.failed_cases
        ):
            return
        try:
            self._sync_status_inbound(job_case)
            self._sync_status_outbound(job_case)
        except Exception:
            self.logger.exception(
                f"Failed to sync status for case {job_case.case_detail.id_}."
            )

    def _sync_status_inbound(self, job_case: JobCase) -> None:
        full_mapping: dict[str, list[AlertCard]] = self.case_threat_alerts.get(
            job_case.case_detail.id_, {}
        )
        if not full_mapping:
            full_mapping = {
                tid: [alert]
                for tid, alert in job_case.product_ids_from_secops_alerts.items()
            }
        for threat_id, alerts in full_mapping.items():
            for alert in alerts:
                self._sync_single_alert_status_inbound(job_case, threat_id, alert)
        self._evaluate_overall_case_closure(job_case)

    def _sync_single_alert_status_inbound(
        self, job_case: JobCase, threat_id: str, alert: AlertCard
    ) -> None:
        meta: SyncMetadata | None = job_case.alert_metadata.get(alert.identifier)
        if not meta or not meta.status:
            return
        wiz_status: str = meta.status.upper()
        if wiz_status not in constants.WIZ_CLOSED_STATUSES:
            return
        if alert.status.lower() in {"close", "closed"}:
            return
        comment: str = (
            f"[SecOps & Wiz Sync Job] {threat_id}: Alert was closed because the "
            f"corresponding Wiz Threat was marked {wiz_status}."
        )
        self.sync_product_status_to_case(
            case_id=str(job_case.case_detail.id_),
            alert_id=alert.identifier,
            reason="Inconclusive",
            root_cause="No clear conclusion",
            comment=comment,
        )
        self.logger.info(
            f"Closed alert {alert.identifier} in case {job_case.case_detail.id_} "
            f"due to Wiz threat closure"
        )

    def _evaluate_overall_case_closure(self, job_case: JobCase) -> None:
        all_alerts_closed: bool = all(
            alert.status.lower() in {"close", "closed"} for alert in job_case.case_detail.alerts
        )
        if all_alerts_closed and job_case.case_detail.status != CaseDataStatus.CLOSED:
            self.soar_job.close_case(
                root_cause="Other",
                case_id=job_case.case_detail.id_,
                reason="Closed by Wiz Sync",
                comment="[SecOps & Wiz Sync Job] All alerts closed. Closing the case.",
                alert_identifier=None,
            )
            self.logger.info(
                f"Closed overall case {job_case.case_detail.id_} because all alerts "
                f"are closed."
            )
        elif not all_alerts_closed:
            self._handle_mixed_alert_comments(job_case)

    def _handle_mixed_alert_comments(self, job_case: JobCase) -> None:
        active_non_wiz_alerts: bool = any(
            alert.status.lower() not in {"close", "closed"}
            and not self._extract_clean_threat_id(self._get_wiz_threat_id(alert))
            for alert in job_case.case_detail.alerts
        )
        if not active_non_wiz_alerts:
            return
        has_mixed_comment: bool = any(
            "[SecOps & Wiz Sync Job] Mixed Alert Resolution" in c.get("comment", "")
            for c in job_case.case_comments
        )
        if has_mixed_comment:
            return
        comment_text: str = (
            "[SecOps & Wiz Sync Job] Mixed Alert Resolution. A mapped Wiz Threat "
            "has been resolved. Mapped Wiz Alerts inside this case have been "
            "automatically closed. The overall SecOps Case remains open because it "
            "contains active alerts from other non-Wiz sources."
        )
        self.soar_job.add_comment(
            case_id=job_case.case_detail.id_,
            comment=comment_text,
            alert_identifier=None,
        )

    def _sync_status_outbound(self, job_case: JobCase) -> None:
        if job_case.case_detail.status != CaseDataStatus.CLOSED:
            return
        wiz_reason: str = self._determine_wiz_resolution_reason(job_case)
        threat_ids: list[str] = self._extract_product_ids_from_case(job_case)
        for threat_id in threat_ids:
            self._sync_single_threat_status_outbound(job_case, threat_id, wiz_reason)

    @staticmethod
    def _determine_wiz_resolution_reason(job_case: JobCase) -> str:
        close_reason: str = (
            getattr(job_case.case_detail, "close_reason", "REASON_UNSPECIFIED")
            or "REASON_UNSPECIFIED"
        )
        close_verdict: int = getattr(job_case.case_detail, "close_verdict", 0) or 0
        if close_reason in constants.CLOSE_REASON_TO_WIZ_REASON:
            return constants.CLOSE_REASON_TO_WIZ_REASON[close_reason]
        if close_reason == "REASON_UNSPECIFIED":
            return constants.CLOSE_VERDICT_TO_WIZ_REASON.get(
                close_verdict, constants.WIZ_REASON_INCONCLUSIVE_THREAT
            )
        return constants.WIZ_REASON_INCONCLUSIVE_THREAT

    def _update_wiz_threat_status(self, threat_id: str, wiz_reason: str) -> tuple[str, str]:
        """Update the threat status on Wiz according to the SecOps resolution reason.

        Args:
            threat_id (str): The Wiz Threat ID.
            wiz_reason (str): The determined Wiz resolution reason.

        Returns:
            tuple[str, str]: Target status and reason for logging.

        """
        if wiz_reason == constants.WIZ_REASON_FALSE_POSITIVE:
            self.api_client.ignore_issue(
                issue_id=threat_id,
                resolution_reason="False Positive",
                note="Closed via SecOps Case Sync",
            )
            return constants.STATUS_REJECTED, constants.WIZ_REASON_FALSE_POSITIVE

        if wiz_reason == constants.WIZ_REASON_MALICIOUS_THREAT:
            self.api_client.resolve_issue(
                issue_id=threat_id,
                resolution_reason="Malicious Threat",
                resolution_note="Closed via SecOps Case Sync",
            )
            return constants.STATUS_RESOLVED, constants.WIZ_REASON_MALICIOUS_THREAT

        if wiz_reason == constants.WIZ_REASON_PLANNED_ACTION_THREAT:
            self.api_client.resolve_issue(
                issue_id=threat_id,
                resolution_reason="Planned Action Threat",
                resolution_note="Closed via SecOps Case Sync",
            )
            return constants.STATUS_RESOLVED, constants.WIZ_REASON_PLANNED_ACTION_THREAT

        self.api_client.resolve_issue(
            issue_id=threat_id,
            resolution_reason="Inconclusive Threat",
            resolution_note="Closed via SecOps Case Sync",
        )
        return constants.STATUS_RESOLVED, constants.WIZ_REASON_INCONCLUSIVE_THREAT

    def _sync_single_threat_status_outbound(
        self, job_case: JobCase, threat_id: str, wiz_reason: str
    ) -> None:
        alerts: list[AlertCard] = self.case_threat_alerts.get(
            job_case.case_detail.id_, {}
        ).get(threat_id, [])
        meta: SyncMetadata | None = None
        if alerts:
            meta = job_case.alert_metadata.get(alerts[0].identifier)
        if (
            meta
            and meta.status
            and meta.status.upper() in constants.WIZ_CLOSED_STATUSES
        ):
            return
        try:
            target_status_log, target_reason_log = self._update_wiz_threat_status(
                threat_id, wiz_reason
            )
            self.logger.info(
                f"Closed Wiz threat {threat_id} (Status: {target_status_log}, "
                f"Reason: {target_reason_log})"
            )
            comment_text: str = (
                f"[SecOps & Wiz Sync Job] SecOps Case {job_case.case_detail.id_} "
                f"status was updated to CLOSED on "
                f"{datetime.now(UTC).isoformat()} by system. Wiz Threat "
                f"{threat_id} status has been automatically updated to "
                f"{target_status_log} (Resolution Reason: {target_reason_log}) "
                f"in response."
            )
            self.soar_job.add_comment(
                case_id=job_case.case_detail.id_,
                comment=comment_text,
                alert_identifier=None,
            )
        except Exception:
            self.logger.exception(f"Failed to close Wiz threat {threat_id}.")

    def sync_severity(self, job_case: JobCase) -> None:
        """Synchronize severity from Wiz to SecOps (strictly unidirectional escalation).

        Args:
            job_case (JobCase): The SecOps case.

        """
        if (
            not self.sync_severity_enabled
            or job_case.case_detail.id_ in self.failed_cases
        ):
            return
        try:
            for alert in job_case.case_detail.alerts:
                self._sync_single_alert_severity(job_case, alert)
        except Exception:
            self.logger.exception(
                f"Failed to sync severity for case {job_case.case_detail.id_}."
            )

    def _sync_single_alert_severity(self, job_case: JobCase, alert: AlertCard) -> None:
        threat_id: str | None = self._extract_clean_threat_id(
            self._get_wiz_threat_id(alert)
        )
        if not threat_id:
            return
        meta: SyncMetadata | None = job_case.alert_metadata.get(alert.identifier)
        if not meta or not meta.severity:
            return
        wiz_severity: str = meta.severity.upper()
        wiz_weight: int = constants.WIZ_SEVERITY_WEIGHTS.get(wiz_severity, 0)
        current_priority: str = alert.priority or "Informational"
        secops_weight: int = constants.SECOPS_PRIORITY_WEIGHTS.get(
            current_priority.lower(), 0
        )
        if wiz_weight > secops_weight:
            self._escalate_alert_priority(
                job_case, alert, threat_id, wiz_severity, current_priority
            )

    def _escalate_alert_priority(
        self,
        job_case: JobCase,
        alert: AlertCard,
        threat_id: str,
        wiz_severity: str,
        current_priority: str,
    ) -> None:
        target_priority: str = constants.WIZ_TO_SECOPS_PRIORITY.get(
            wiz_severity, "Informational"
        )
        self.sync_severity_to_case(
            alert_identifier=alert.identifier,
            alert_name=alert.name,
            case_id=str(job_case.case_detail.id_),
            new_priority=target_priority,
        )
        self.logger.info(
            f"Escalated priority of alert {alert.identifier} to {target_priority}"
        )

        key = (job_case.case_detail.id_, threat_id, target_priority)
        if key in self._escalated_threats:
            return

        comment: str = (
            f"[SecOps & Wiz Sync Job] Severity Escalation. Mapped Wiz Threat {threat_id} "
            f"severity {wiz_severity} is higher than current SecOps Case priority {current_priority}. "
            f"Case priority has been automatically escalated to {target_priority} to align "
            f"with the higher risk level."
        )
        self.soar_job.add_comment(
            case_id=job_case.case_detail.id_,
            comment=comment,
            alert_identifier=alert.identifier,
        )
        self._escalated_threats.add(key)

    def sync_comments(self, job_case: JobCase) -> None:
        """Synchronize comments bidirectionally between Wiz and SecOps.

        Args:
            job_case (JobCase): The SecOps case.

        """
        if (
            not self.sync_comments_enabled
            or job_case.case_detail.id_ in self.failed_cases
        ):
            return
        try:
            job_case.case_comments = self.soar_job.fetch_case_comments(
                case_id=job_case.case_detail.id_,
            )
            job_case.__class__ = WizJobCase

            comments_to_sync: Any = self.get_comments_to_sync(
                job_case=job_case,
                product_comment_prefix="[Wiz Note] ",
                case_comment_prefix="[SecOps & Wiz Sync Job] ",
                product_comment_key="message",
                product_incident_key="issue_id",
            )
            self.sync_product_comments_to_case(
                case_id=job_case.case_detail.id_,
                comments=comments_to_sync.product_comments_sync_to_case,
            )
            self.sync_case_comments_to_product(
                job_case=job_case,
                comments=comments_to_sync.case_comments_sync_to_product,
            )
        except Exception:
            self.logger.exception(
                f"Failed to sync comments for case {job_case.case_detail.id_}."
            )

    def sync_case_comments_to_product(
        self, job_case: JobCase, comments: list[str]
    ) -> None:
        """Push SOAR Case comments to Wiz as issue notes.

        Args:
            job_case (JobCase): The SecOps case.
            comments (list[str]): The list of comments to sync.

        """
        threat_ids: list[str] = self._extract_product_ids_from_case(job_case)
        if not threat_ids:
            return
        for comment_str in comments:
            self._sync_single_comment_to_all_threats(
                job_case, threat_ids, comment_str
            )

    def _sync_single_comment_to_all_threats(
        self, job_case: JobCase, threat_ids: list[str], comment_str: str
    ) -> None:
        original_comment: dict[str, Any] | None = (
            self._find_original_case_comment(job_case, comment_str)
        )
        if original_comment:
            comment_text: str = original_comment.get("comment", "")
            if comment_text.startswith("[SecOps & Wiz Sync Job] "):
                return
        formatted_text: str = self._format_outbound_comment(
            comment_str, original_comment
        )
        for threat_id in threat_ids:
            self._add_comment_to_wiz_issue(threat_id, formatted_text)

    @staticmethod
    def _find_original_case_comment(
        job_case: JobCase, comment_str: str
    ) -> dict[str, Any] | None:
        prefix = f"[SecOps & Wiz Sync Job] {job_case.case_detail.id_}: "
        if comment_str.startswith(prefix):
            target_text = comment_str[len(prefix) :]
            for c in job_case.case_comments:
                if c.get("comment", "") == target_text:
                    return c
        return None

    @staticmethod
    def _format_outbound_comment(
        comment_str: str, original_comment: dict[str, Any] | None
    ) -> str:
        if not original_comment:
            return comment_str
        creator: str = (
            original_comment.get("creator_full_name")
            or original_comment.get("creator_user_id")
            or "analyst@company.com"
        )
        creation_time_ms: int = (
            original_comment.get("creation_time_unix_time_in_ms")
            or constants.FALLBACK_TIMESTAMP
        )
        creation_time_str: str = datetime.fromtimestamp(
            creation_time_ms / constants.MS_TO_SEC_DIVISOR, tz=UTC
        ).isoformat()
        return (
            f"[SecOps & Wiz Sync Job] {creator} wrote in Google SecOps on "
            f"{creation_time_str}: {original_comment.get('comment', '')}"
        )

    def _add_comment_to_wiz_issue(self, threat_id: str, formatted_text: str) -> None:
        try:
            self.api_client.add_comment_to_issue(
                issue_id=threat_id,
                comment=formatted_text,
            )
            self.logger.info(f"Synced comment to Wiz threat {threat_id}")
        except Exception:
            self.logger.exception(
                f"Failed to sync comment to Wiz threat {threat_id}."
            )

    def _finalize(self) -> None:
        if not self.sync_product_link_enabled:
            return
        try:
            client_address: str = os.environ.get(
                "CLIENT_ADDRESS", "https://backstory.chronicle.security"
            ).rstrip("/")
            if not client_address.startswith("http://") and not client_address.startswith("https://"):
                client_address = f"https://{client_address}"
            for job_case in self.job_cases_to_sync:
                self._finalize_single_case(job_case, client_address)
        except Exception:
            self.logger.exception(
                "Failed to perform link-back finalization."
            )

    def _finalize_single_case(
        self, job_case: JobCase, client_address: str
    ) -> None:
        if job_case.case_detail.id_ in self.failed_cases:
            return
        ticket_url: str = f"{client_address}/cases/{job_case.case_detail.id_}"
        threat_ids: list[str] = self._extract_product_ids_from_case(job_case)
        for threat_id in threat_ids:
            self._associate_ticket_to_threat(job_case, threat_id, ticket_url)

    def _associate_ticket_to_threat(
        self, job_case: JobCase, threat_id: str, ticket_url: str
    ) -> None:
        try:
            self.api_client.associate_service_ticket(
                issue_id=threat_id,
                ticket_id=str(job_case.case_detail.id_),
                ticket_url=ticket_url,
            )
            self.logger.info(
                f"Successfully associated SecOps case {job_case.case_detail.id_} "
                f"to Wiz threat {threat_id}"
            )
        except Exception:
            self.logger.exception(
                f"Failed to associate SecOps case link to Wiz threat {threat_id}."
            )


class WizJobCase(JobCase):
    __slots__ = ()

    def get_product_comments_hashes(self) -> list[str]:
        """Get product comments hashes formatted as SecOps comments for deduplication check.

        Returns:
            list[str]: The list of formatted string hashes.

        """
        comments_hashes = []
        for alert in self.case_detail.alerts:
            if not hasattr(alert, "incident") or alert.incident is None:
                continue
            for comment in alert.incident.comments:
                message = comment.message or ""
                if "[SecOps & Wiz Sync Job] " in message and " wrote in Google SecOps on " in message:
                    idx = message.find(" wrote in Google SecOps on ")
                    header_end_idx = message.find(": ", idx)
                    if header_end_idx != -1:
                        original_text = message[header_end_idx + 2 :]
                        formatted = f"[SecOps & Wiz Sync Job] {self.case_detail.id_}: {original_text}"
                        comments_hashes.append(self._generate_string_hash(formatted))
                        continue
                comments_hashes.append(self._generate_string_hash(message))
        return comments_hashes


def main() -> NoReturn:
    """Start the sync job execution."""
    WizSecopsBidirectionalSyncJob().start()


if __name__ == "__main__":
    main()
