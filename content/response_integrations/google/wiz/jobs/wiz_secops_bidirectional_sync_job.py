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
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, NoReturn

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import CaseDataStatus
from TIPCommon.soar_ops import get_users_profile_cards_with_pagination

from ..core import action_init, constants
from ..core.api_client import WizApiClient
from ..core.datamodels import WizIncidentComment

if TYPE_CHECKING:
    from TIPCommon.data_models import AlertCard
    from TIPCommon.types import SingleJson

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
        self._parse_fields_to_sync()
        client: WizApiClient = action_init.create_api_client(self.soar_job)
        return client

    def _parse_fields_to_sync(self) -> None:
        raw_fields: str | None = None
        if hasattr(self.params, "fieldstosync"):
            val: Any = self.params.fieldstosync
            if isinstance(val, str):
                raw_fields = val
        if raw_fields is None and hasattr(self.params, "fields_to_sync"):
            val: Any = self.params.fields_to_sync
            if isinstance(val, str):
                raw_fields = val
        if raw_fields is None:
            raw_fields = "Status, Comments, Product Link, Severity"

        fields_to_sync: list[str] = [f.strip().lower() for f in raw_fields.split(",")]
        self.sync_status_enabled = "status" in fields_to_sync
        self.sync_comments_enabled = "comments" in fields_to_sync
        self.sync_product_link_enabled = "product link" in fields_to_sync
        self.sync_severity_enabled = "severity" in fields_to_sync

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
        last_part: str = threat_id.split("_")[constants.NOT_FOUND_INDEX]
        if len(last_part) == constants.UUID_LENGTH and "-" in last_part:
            return last_part
        return threat_id

    def _get_wiz_threat_id(self, alert: AlertCard) -> str | None:
        if not alert.additional_properties:
            return None
        try:
            props: SingleJson = json.loads(alert.additional_properties)
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
            self._wiz_alerts_closed_this_run = False
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
        if wiz_status in constants.WIZ_CLOSED_STATUSES:
            self._close_alert_inbound(job_case, threat_id, alert, wiz_status)
        else:
            self._reopen_alert_inbound(job_case, threat_id, alert, wiz_status)

    def _close_alert_inbound(
        self, job_case: JobCase, threat_id: str, alert: AlertCard, wiz_status: str
    ) -> None:
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
        self._wiz_alerts_closed_this_run = True
        self.logger.info(
            f"Closed alert {alert.identifier} in case {job_case.case_detail.id_} "
            f"due to Wiz threat closure"
        )

    def _reopen_alert_inbound(
        self, job_case: JobCase, threat_id: str, alert: AlertCard, wiz_status: str
    ) -> None:
        if alert.status.lower() not in {"close", "closed"}:
            return
        previous_status: str | None = self._get_last_synced_wiz_status_from_comments(
            job_case, threat_id
        )
        if previous_status not in constants.WIZ_CLOSED_STATUSES:
            return
        self._reopen_alert_in_secops(str(job_case.case_detail.id_), alert.identifier)
        alert.status = "opened"
        comment: str = (
            f"[SecOps & Wiz Sync Job] Alert {alert.name} was reopened because the corresponding "
            f"Wiz Threat status was updated to {wiz_status}."
        )
        self.soar_job.add_comment(
            case_id=job_case.case_detail.id_,
            comment=comment,
            alert_identifier=alert.identifier,
        )
        self.logger.info(
            f"Reopened alert {alert.identifier} in case {job_case.case_detail.id_} "
            f"due to Wiz threat reopen"
        )

    def _get_last_synced_wiz_status_from_comments(
        self, job_case: JobCase, threat_id: str
    ) -> str | None:
        alerts: list[AlertCard] = job_case.case_detail.alerts
        for comment_dict in reversed(getattr(job_case, "case_comments", [])):
            comment: str = comment_dict.get("comment", "")
            if not comment.startswith(constants.SYNC_COMMENT_PREFIX):
                continue

            status: str | None = self._parse_wiz_status_from_closed_comment(comment, threat_id)
            if status:
                return status

            status = self._parse_wiz_status_from_reopen_comment(comment, threat_id, alerts)
            if status:
                return status

            status = self._parse_wiz_status_from_auto_closed_comment(comment, threat_id)
            if status:
                return status

        return None

    @staticmethod
    def _parse_wiz_status_from_closed_comment(comment: str, threat_id: str) -> str | None:
        if f"{threat_id}: Alert was closed" in comment:
            match: re.Match | None = re.search(r"marked\s+([A-Z_]+)", comment, re.IGNORECASE)
            if match:
                return match.group(constants.STATUS_CAPTURE_GROUP).upper()
        return None

    def _parse_wiz_status_from_reopen_comment(
        self, comment: str, threat_id: str, alerts: list[AlertCard]
    ) -> str | None:
        if constants.WIZ_REOPENED_COMMENT_SUBSTRING in comment:
            alert: AlertCard | None = next(
                (
                    a for a in alerts
                    if self._extract_clean_threat_id(self._get_wiz_threat_id(a)) == threat_id
                ),
                None,
            )
            if alert and f"Alert {alert.name} was reopened" in comment:
                match: re.Match | None = re.search(
                    r"updated to\s+([A-Z_]+)", comment, re.IGNORECASE
                )
                if match:
                    return match.group(constants.STATUS_CAPTURE_GROUP).upper()
        return None

    @staticmethod
    def _parse_wiz_status_from_auto_closed_comment(comment: str, threat_id: str) -> str | None:
        if f"Wiz Threat {threat_id} status has been automatically updated to" in comment:
            match: re.Match | None = re.search(
                r"automatically updated to\s+([A-Z_]+)", comment, re.IGNORECASE
            )
            if match:
                return match.group(constants.STATUS_CAPTURE_GROUP).upper()
        return None

    def _reopen_alert_in_secops(self, case_id: str, alert_id: str) -> None:
        url = f"{self.soar_job.API_ROOT}/external/v1/dynamic-cases/ReopenAlert"
        payload = {
            "caseId": int(case_id),
            "alertIdentifier": alert_id,
        }
        response = self.soar_job.session.post(url, json=payload)
        try:
            response.raise_for_status()
        except Exception:
            self.logger.exception(
                f"ReopenAlert failed with status {response.status_code}. "
                f"Response body: {response.text}"
            )
            raise

    def _reopen_case_in_secops(self, case_id: str) -> None:
        url = f"{self.soar_job.API_ROOT}/external/v1/cases/ExecuteBulkReopenCase"
        payload = [int(case_id)]
        response = self.soar_job.session.post(url, json=payload)
        response.raise_for_status()

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
        elif not all_alerts_closed and job_case.case_detail.status == CaseDataStatus.CLOSED:
            self._reopen_case_in_secops(str(job_case.case_detail.id_))
            self.logger.info(
                f"Reopened overall case {job_case.case_detail.id_} because alert was "
                f"reopened."
            )
        elif not all_alerts_closed:
            self._handle_mixed_alert_comments(job_case)

    def _handle_mixed_alert_comments(self, job_case: JobCase) -> None:
        if not self._wiz_alerts_closed_this_run:
            return
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
        threat_ids: list[str] = self._extract_product_ids_from_case(job_case)
        full_mapping: dict[str, list[AlertCard]] = self.case_threat_alerts.get(
            job_case.case_detail.id_, {}
        )
        if not full_mapping:
            full_mapping = {
                tid: [alert]
                for tid, alert in job_case.product_ids_from_secops_alerts.items()
            }

        for threat_id in threat_ids:
            alerts: list[AlertCard] = full_mapping.get(threat_id, [])
            if not alerts:
                continue

            all_threat_alerts_closed: bool = (
                job_case.case_detail.status == CaseDataStatus.CLOSED
                or all(
                    alert.status.lower() in {"close", "closed"}
                    for alert in alerts
                )
            )
            if not all_threat_alerts_closed:
                continue

            wiz_reason: str = self._determine_wiz_resolution_reason(job_case)
            self._sync_single_threat_status_outbound(job_case, threat_id, wiz_reason, alerts)

    @staticmethod
    def _determine_wiz_resolution_reason(job_case: JobCase) -> str:
        close_reason: str = (
            getattr(job_case.case_detail, "close_reason", "REASON_UNSPECIFIED")
            or "REASON_UNSPECIFIED"
        )
        close_verdict: int = getattr(
            job_case.case_detail, "close_verdict", constants.DEFAULT_FALLBACK_VALUE
        ) or constants.DEFAULT_FALLBACK_VALUE
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
        self, job_case: JobCase, threat_id: str, wiz_reason: str, alerts: list[AlertCard]
    ) -> None:
        meta: SyncMetadata | None = None
        if alerts:
            meta = job_case.alert_metadata.get(alerts[constants.DEFAULT_FALLBACK_VALUE].identifier)
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
        except Exception:
            self.logger.exception(f"Failed to close Wiz threat {threat_id}.")
            return

        self.logger.info(
            f"Closed Wiz threat {threat_id} (Status: {target_status_log}, "
            f"Reason: {target_reason_log})"
        )
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        comment_text: str = (
            f"[SecOps & Wiz Sync Job] SecOps Case {job_case.case_detail.id_} "
            f"status was updated to CLOSED on "
            f"{now_str} by system. Wiz Threat {threat_id} status has been "
            f"automatically updated to {target_status_log} (Resolution Reason: {target_reason_log}) "
            f"in response."
        )
        try:
            self.soar_job.add_comment(
                case_id=job_case.case_detail.id_,
                comment=comment_text,
                alert_identifier=None,
            )
            self._add_comment_to_wiz_issue(threat_id, comment_text)
        except Exception:
            self.logger.exception(f"Failed to write closure comments for Wiz threat {threat_id}.")

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
        wiz_weight: int = constants.WIZ_SEVERITY_WEIGHTS.get(wiz_severity, constants.DEFAULT_FALLBACK_VALUE)
        current_priority: str = alert.priority or "Informational"
        secops_weight: int = constants.SECOPS_PRIORITY_WEIGHTS.get(
            current_priority.lower(), constants.DEFAULT_FALLBACK_VALUE
        )
        if secops_weight > wiz_weight:
            self._add_outbound_severity_comment_to_wiz(
                job_case, threat_id, current_priority
            )

        previous_wiz_severity = self._get_last_synced_wiz_severity_from_comments(job_case, threat_id)
        if previous_wiz_severity == wiz_severity:
            if wiz_weight > secops_weight:
                self._escalate_alert_priority(
                    job_case, alert, threat_id, wiz_severity, previous_wiz_severity
                )
            return

        if wiz_weight > secops_weight:
            self._escalate_alert_priority(
                job_case, alert, threat_id, wiz_severity, previous_wiz_severity
            )
        else:
            self._log_ignored_downgrade(
                job_case, alert, threat_id, wiz_severity, previous_wiz_severity
            )

    @staticmethod
    def _is_severity_comment_present(
        job_case: JobCase, comment_text: str
    ) -> bool:
        for comment_dict in getattr(job_case, "case_comments", []):
            if comment_dict.get("comment", "") == comment_text:
                return True
        return False

    @staticmethod
    def _get_last_synced_wiz_severity_from_comments(
        job_case: JobCase, threat_id: str
    ) -> str | None:
        pattern = re.compile(
            rf"(?:Wiz Threat {threat_id} severity (?:decreased|increased) to"
            rf"|Mapped Wiz Threat {threat_id} severity)\s+([A-Z]+)",
            re.IGNORECASE,
        )
        for comment_dict in reversed(getattr(job_case, "case_comments", [])):
            comment_text = comment_dict.get("comment", "")
            match = pattern.search(comment_text)
            if match:
                return match.group(1).upper()
        return None

    @staticmethod
    def _get_severity_update_direction(
        wiz_severity: str,
        previous_wiz_severity: str | None,
        secops_priority: str,
    ) -> str:
        wiz_weight = constants.WIZ_SEVERITY_WEIGHTS.get(wiz_severity, constants.DEFAULT_FALLBACK_VALUE)
        if not previous_wiz_severity:
            secops_weight = constants.SECOPS_PRIORITY_WEIGHTS.get(
                secops_priority.lower(), constants.DEFAULT_FALLBACK_VALUE
            )
            return "decreased" if wiz_weight < secops_weight else "increased"

        prev_weight = constants.WIZ_SEVERITY_WEIGHTS.get(
            previous_wiz_severity, constants.DEFAULT_FALLBACK_VALUE
        )
        if wiz_weight > prev_weight:
            return "increased"
        if wiz_weight < prev_weight:
            return "decreased"
        return "remains"

    def _escalate_alert_priority(
        self,
        job_case: JobCase,
        alert: AlertCard,
        threat_id: str,
        wiz_severity: str,
        previous_wiz_severity: str | None,
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

        direction = self._get_severity_update_direction(
            wiz_severity, previous_wiz_severity, target_priority
        )
        action_text = f"remains {wiz_severity}" if direction == "remains" else f"{direction} to {wiz_severity}"

        comment: str = (
            f"[SecOps & Wiz Sync Job] Severity Update: Wiz Threat {threat_id} "
            f"severity {action_text}. SecOps priority has been "
            f"escalated to {target_priority} to align with the higher risk level."
        )

        if self._is_severity_comment_present(job_case, comment):
            return

        self.soar_job.add_comment(
            case_id=job_case.case_detail.id_,
            comment=comment,
            alert_identifier=alert.identifier,
        )
        self._escalated_threats.add(key)

    def _log_ignored_downgrade(
        self,
        job_case: JobCase,
        alert: AlertCard,
        threat_id: str,
        wiz_severity: str,
        previous_wiz_severity: str | None,
    ) -> None:
        key = (job_case.case_detail.id_, threat_id, wiz_severity, "downgrade")
        if key in self._escalated_threats:
            return

        current_priority = alert.priority or "Informational"
        direction = self._get_severity_update_direction(
            wiz_severity, previous_wiz_severity, current_priority
        )
        if direction == "remains":
            return

        action_text = f"{direction} to {wiz_severity}"
        comment: str = (
            f"[SecOps & Wiz Sync Job] Severity Update: Wiz Threat {threat_id} "
            f"severity {action_text}. SecOps priority remains {current_priority} "
            f"to preserve the established risk context."
        )

        if self._is_severity_comment_present(job_case, comment):
            return

        self.soar_job.add_comment(
            case_id=job_case.case_detail.id_,
            comment=comment,
            alert_identifier=alert.identifier,
        )
        self._escalated_threats.add(key)
        self.logger.info(
            f"Ignored downgrade of alert {alert.identifier} priority from {current_priority} "
            f"to Wiz severity {wiz_severity}."
        )

    @staticmethod
    def _is_wiz_severity_comment_present(
        threat: Issue, current_priority: str
    ) -> bool:
        match_str = (
            f"[SecOps & Wiz Sync Job] Severity Update: The associated SecOps case severity "
            f"was increased to {current_priority}."
        )
        return any(
            comment.message.startswith(match_str)
            for comment in getattr(threat, "comments", [])
        )

    def _add_outbound_severity_comment_to_wiz(
        self, job_case: JobCase, threat_id: str, current_priority: str
    ) -> None:
        alert = next(
            (
                a for a in job_case.case_detail.alerts
                if self._extract_clean_threat_id(self._get_wiz_threat_id(a)) == threat_id
            ),
            None
        )
        if not alert or not getattr(alert, "incident", None):
            return

        threat = alert.incident

        if self._is_wiz_severity_comment_present(threat, current_priority):
            return

        comment = (
            f"[SecOps & Wiz Sync Job] Severity Update: The associated SecOps case severity "
            f"was increased to {current_priority}. Wiz severity remains unchanged to preserve "
            f"the original finding context. SecOps updates do not override Wiz severity."
        )
        try:
            self._add_comment_to_wiz_issue(threat_id, comment)
            self.logger.info(f"Successfully posted severity update comment to Wiz threat {threat_id}")
            if not hasattr(threat, "comments") or threat.comments is None:
                threat.comments = []
            threat.comments.append(WizIncidentComment({"text": comment}))
        except Exception:
            self.logger.exception(f"Failed to post severity update comment to Wiz threat {threat_id}")

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
                product_comment_prefix=f"{constants.SYNC_COMMENT_PREFIX} ",
                case_comment_prefix=f"{constants.SYNC_COMMENT_PREFIX} ",
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
        original_comment: SingleJson | None = (
            self._find_original_case_comment(job_case, comment_str)
        )
        if original_comment:
            comment_text: str = original_comment.get("comment", "")
            if comment_text.startswith(f"{constants.SYNC_COMMENT_PREFIX} "):
                return
        formatted_text: str = self._format_outbound_comment(
            comment_str, original_comment
        )
        for threat_id in threat_ids:
            self._add_comment_to_wiz_issue(threat_id, formatted_text)

    @staticmethod
    def _find_original_case_comment(
        job_case: JobCase, comment_str: str
    ) -> SingleJson | None:
        prefix: str = f"{constants.SYNC_COMMENT_PREFIX} {job_case.case_detail.id_}: "
        if comment_str.startswith(prefix):
            target_text: str = comment_str[len(prefix) :]
            for c in job_case.case_comments:
                if c.get("comment", "") == target_text:
                    return c
        return None

    def _get_secops_user_email(self, user_id: str) -> str | None:
        if not hasattr(self, "_secops_users_cache"):
            self._secops_users_cache: dict[str, str] = {}
            try:
                users = get_users_profile_cards_with_pagination(self.soar_job)
                for u in users:
                    uuid_str: str = u.user_name
                    email: str | None = u.raw_data.get("email") or u.raw_data.get("loginIdentifier")
                    if uuid_str and email:
                        self._secops_users_cache[uuid_str] = email
            except Exception:
                self.logger.exception("Failed to fetch SecOps user profiles")
        return self._secops_users_cache.get(user_id)

    def _format_outbound_comment(
        self, comment_str: str, original_comment: SingleJson | None
    ) -> str:
        if not original_comment:
            return comment_str
        creator_user_id: str | None = original_comment.get("creator_user_id")
        creator: str = (
            original_comment.get("creator_email_address")
            or (self._get_secops_user_email(creator_user_id) if creator_user_id else None)
            or original_comment.get("creator_full_name")
            or original_comment.get("creator_user_id")
            or "analyst@company.com"
        )
        creation_time_ms: int = (
            original_comment.get("creation_time_unix_time_in_ms")
            or constants.FALLBACK_TIMESTAMP
        )
        creation_time_dt: datetime = datetime.fromtimestamp(
            creation_time_ms / constants.MS_TO_SEC_DIVISOR, tz=UTC
        )
        creation_time_str: str = creation_time_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        comment_text: str = original_comment.get("comment", "")
        return (
            f"{constants.SYNC_COMMENT_PREFIX} {creator}{constants.WROTE_IN_SECOPS_SIGNATURE}"
            f"{creation_time_str}: {comment_text}"
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
        ticket_id = str(job_case.case_detail.id_)
        alert = job_case.product_ids_from_secops_alerts.get(threat_id)
        if alert and getattr(alert, "incident", None):
            threat = alert.incident
            already_linked = any(
                ticket.external_id == ticket_id
                for ticket in getattr(threat, "service_tickets", [])
            )
            if already_linked:
                self.logger.info(
                    f"SecOps case {ticket_id} is already associated to Wiz threat {threat_id}."
                )
                return
        try:
            self.api_client.associate_service_ticket(
                issue_id=threat_id,
                ticket_id=ticket_id,
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

    def _map_threat_to_cases(self, threat: Issue, modified_cases: list[tuple[str, int]]) -> None:
        """Map a modified threat to its corresponding SecOps cases.

        Args:
            threat (Issue): The threat issue.
            modified_cases (list[tuple[str, int]]): The list of modified case tuples to append to.

        """
        threat_id = threat.issue_id
        try:
            clean_time = threat.updated_at.replace("Z", "+00:00")
            updated_at_dt = datetime.fromisoformat(clean_time)
        except (ValueError, TypeError):
            updated_at_dt = datetime.now(UTC)

        latest_comment_dt, _ = self._get_latest_comment_details(threat)
        if latest_comment_dt:
            updated_at_dt = max(updated_at_dt, latest_comment_dt)

        updated_at_ms = int(updated_at_dt.timestamp() * constants.MS_TO_S_FACTOR)

        for case_id, t_ids in self.processed_items.items():
            if threat_id in t_ids:
                modified_cases.append((case_id, updated_at_ms))

    def _get_last_run_datetime(self) -> datetime:
        last_run_time_ms = self.last_run_time
        if last_run_time_ms <= constants.DEFAULT_FALLBACK_VALUE:
            hours_back = getattr(self.params, "max_hours_backwards", constants.HOURS_BACK_24)
            try:
                hours_back = int(hours_back)
            except ValueError:
                hours_back = constants.HOURS_BACK_24
            return datetime.now(UTC) - timedelta(hours=hours_back)
        return datetime.fromtimestamp(
            (last_run_time_ms + constants.MS_TO_S_FACTOR) / float(constants.MS_TO_S_FACTOR), tz=UTC
        )

    @staticmethod
    def _get_latest_comment_details(
        threat: Issue
    ) -> tuple[datetime | None, bool]:
        """Get the latest comment's creation time and check if it is an automation comment.

        Args:
            threat (Issue): The threat issue.

        Returns:
            tuple[datetime | None, bool]: A tuple containing the latest comment's datetime
                (or None if no comments exist) and a boolean indicating if it is an automation comment.

        """
        if not threat.comments:
            return None, False

        sorted_comments = sorted(
            threat.comments,
            key=lambda c: c.raw_comment.get("createdAt", ""),
        )
        latest_comment = sorted_comments[constants.NOT_FOUND_INDEX]
        is_automation = latest_comment.message.startswith(
            constants.SYNC_COMMENT_PREFIX
        )

        try:
            c_time = latest_comment.raw_comment.get("createdAt", "").replace(
                "Z", "+00:00"
            )
            return datetime.fromisoformat(c_time), is_automation
        except (ValueError, TypeError):
            return None, is_automation

    def modified_synced_case_ids_by_product(
        self,
        product_ids: list[str],
        _case_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Fetch modified synced case IDs based on the modified Wiz threats.

        Args:
            product_ids (list[str]): A list of modified product IDs.
            _case_ids (list[tuple[str, int]]): A list of case IDs.

        Returns:
            list[tuple[str, int]]: A list of modified synced case IDs.

        """
        product_ids_list: list[str] = list(product_ids)
        if not product_ids_list:
            return []

        last_run_dt: datetime = self._get_last_run_datetime()
        updated_threats: list[Issue] = self._get_updated_threats_since_last_run(last_run_dt)
        if not updated_threats:
            return []

        modified_cases: list[tuple[str, int]] = []
        for threat in updated_threats:
            if threat.issue_id not in product_ids_list:
                continue

            if self._is_threat_modified_since_last_run(threat, last_run_dt):
                self._map_threat_to_cases(threat, modified_cases)

        return modified_cases

    def _get_updated_threats_since_last_run(self, last_run_dt: datetime) -> list[Issue]:
        updated_after_iso: str = last_run_dt.isoformat().replace("+00:00", "Z")
        try:
            return self.api_client.get_updated_threats(updated_after=updated_after_iso)
        except Exception:
            self.logger.exception("Failed to fetch updated threats from Wiz.")
            return []

    def _is_threat_modified_since_last_run(self, threat: Issue, last_run_dt: datetime) -> bool:
        try:
            clean_time: str = threat.updated_at.replace("Z", "+00:00")
            updated_at_dt: datetime = datetime.fromisoformat(clean_time)
        except (ValueError, TypeError):
            updated_at_dt: datetime = datetime.now(UTC)

        latest_comment_dt: datetime | None
        is_latest_comment_automation: bool
        latest_comment_dt, is_latest_comment_automation = self._get_latest_comment_details(threat)

        is_threat_updated: bool = updated_at_dt > last_run_dt
        is_comment_updated: bool = (
            latest_comment_dt is not None
            and latest_comment_dt > last_run_dt
            and not is_latest_comment_automation
        )

        return is_threat_updated or is_comment_updated


class WizJobCase(JobCase):
    __slots__ = ()

    def get_product_comments_hashes(self) -> list[str]:
        """Get product comments hashes formatted as SecOps comments for deduplication check.

        Returns:
            list[str]: The list of formatted string hashes.

        """
        comments_hashes: list[str] = []
        for alert in self.case_detail.alerts:
            incident: Issue | None = getattr(alert, "incident", None)
            if incident:
                self._collect_incident_comments_hashes(incident, comments_hashes)
        return comments_hashes

    def _collect_incident_comments_hashes(
        self, incident: Issue, comments_hashes: list[str]
    ) -> None:
        for comment in incident.comments:
            message: str = comment.message or ""
            hash_val: str = self._generate_string_hash(
                self._normalize_product_comment(message)
            )
            comments_hashes.append(hash_val)

    def _normalize_product_comment(self, message: str) -> str:
        signature: str = constants.WROTE_IN_SECOPS_SIGNATURE
        prefix: str = f"{constants.SYNC_COMMENT_PREFIX} "
        if prefix in message and signature in message:
            idx: int = message.find(signature)
            header_end_idx: int = message.find(": ", idx)
            if header_end_idx != constants.NOT_FOUND_INDEX:
                original_text: str = message[header_end_idx + constants.COLON_SPACE_OFFSET :]
                return f"{constants.SYNC_COMMENT_PREFIX} {self.case_detail.id_}: {original_text}"
        return message

    @staticmethod
    def _get_clean_wiz_comment_text(text: str) -> str:
        prefix: str = f"{constants.SYNC_COMMENT_PREFIX} "
        if text.startswith(prefix):
            wrote_index: int = text.find(constants.WROTE_IN_WIZ_SIGNATURE)
            if wrote_index != constants.NOT_FOUND_INDEX:
                colon_index: int = text.find(": ", wrote_index)
                if colon_index != constants.NOT_FOUND_INDEX:
                    return text[colon_index + constants.COLON_SPACE_OFFSET :]
        return text

    def _collect_product_comments_to_sync_to_case(
        self,
        _product_prefix: str,
        case_prefix: str,
        comment_key: str,
        _incident_key: str,
        case_hashes: list[str],
    ) -> list[str]:
        results: list[str] = []
        existing_clean_texts: set[str] = {
            self._get_clean_wiz_comment_text(c.get("comment", ""))
            for c in self.case_comments
        }

        def collect_incident_comments(incident: Issue, alert_id: str) -> None:
            for product_comment in incident.comments:
                text: str = getattr(product_comment, comment_key, "")
                if not self._is_valid_product_comment(text, case_prefix):
                    continue

                if text in existing_clean_texts:
                    continue

                formatted: str = self._format_inbound_comment(product_comment, text)
                if self._generate_string_hash(formatted) in case_hashes:
                    continue

                results.append(f"{alert_id}:{formatted}")

        for alert in self.case_detail.alerts:
            incident: Issue | None = getattr(alert, "incident", None)
            if not incident:
                continue

            alert_id: str = alert.alert_group_identifier
            collect_incident_comments(incident, alert_id)

        return results

    def _format_inbound_comment(self, product_comment: WizIncidentComment, text: str) -> str:
        raw: SingleJson = getattr(product_comment, "raw_comment", {})
        user: SingleJson = raw.get("user") or {}
        service_account: SingleJson = raw.get("serviceAccount") or {}
        creator: str = (
            user.get("email")
            or user.get("name")
            or service_account.get("email")
            or service_account.get("name")
            or "wiz_analyst@company.com"
        )
        time_str: str = self._format_inbound_comment_timestamp(raw.get("createdAt"))
        return f"{constants.SYNC_COMMENT_PREFIX} {creator}{constants.WROTE_IN_WIZ_SIGNATURE}{time_str}: {text}"

    @staticmethod
    def _format_inbound_comment_timestamp(created_at_str: str | None) -> str:
        if created_at_str:
            try:
                clean_time: str = created_at_str.replace("Z", "+00:00")
                dt: datetime = datetime.fromisoformat(clean_time)
                return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, TypeError):
                return "unknown time"
        return "unknown time"


def main() -> NoReturn:
    """Start the sync job execution."""
    WizSecopsBidirectionalSyncJob().start()


if __name__ == "__main__":
    main()
