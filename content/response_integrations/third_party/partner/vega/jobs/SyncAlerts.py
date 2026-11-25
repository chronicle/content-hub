"""Sync Alerts — maintain SecOps cases created from Vega signal ingest."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from types import SimpleNamespace

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import CaseDataStatus
from TIPCommon.rest.soar_api import add_tags_to_case_in_bulk, change_case_description, rename_case

from ..core import constants
from ..core.case_insight import build_incident_insight, incident_ids_from_soar_alert
from ..core.mapping import alert_priority, collect_label_tags, incident_case_title, record_severity
from ..core.VegaManager import VegaClientConfig, VegaManager

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

# Direction values accepted in Sync Direction JSON (Vega-named, not XDR).
_DIR_BIDI = "bidirectional"
_DIR_TO_VEGA = "tovega"
_DIR_TO_SECOPS = "tosecops"
_DIR_NONE = "none"

_COMMENT_PREFIX_VEGA = "[Vega]"
_COMMENT_PREFIX_SECOPS = "[SecOps]"


class SyncAlerts(BaseSyncJob[VegaManager]):
    """Bidirectional sync of Vega incident cases (title, description, insight, status)."""

    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_ALERTS_SCRIPT_NAME,
            context_identifier=constants.SYNC_ALERTS_IDENTIFIER,
            # Connector stamps AlertInfo.case_tags with this; required so a busy
            # environment does not fill sync_limit with non-Vega cases.
            tags_identifiers=[constants.SYNC_ALERTS_TAG],
        )
        self.sync_limit = constants.CASES_SYNC_LIMIT
        self.manager: VegaManager | None = None
        self._sync_dirs: dict[str, str] = {
            "status": _DIR_BIDI,
            "comments": _DIR_BIDI,
        }
        self._incident_by_case: dict[str, SingleJson] = {}

    def _init_api_clients(self) -> None:
        self._parse_sync_direction()
        self.manager = VegaManager(
            VegaClientConfig(
                api_root=self.params.api_root,
                access_key_id=self.params.access_key_id,
                access_key=self.params.access_key,
                verify_ssl=bool(self.params.verify_ssl),
            ),
            logger_instance=self.logger,
        )

    def _parse_sync_direction(self) -> None:
        raw = getattr(self.params, "sync_direction", None) or ""
        if not str(raw).strip():
            return
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warn("Sync Direction is not valid JSON; using Bidirectional defaults.")
            return
        if not isinstance(parsed, dict):
            return
        for key, dest in (("Status", "status"), ("Comments", "comments")):
            value = str(parsed.get(key) or "").strip().lower().replace(" ", "")
            if value in {_DIR_BIDI, _DIR_TO_VEGA, _DIR_TO_SECOPS, _DIR_NONE}:
                self._sync_dirs[dest] = value
            elif value in {"toxdr"}:
                # Accept legacy spelling if pasted from another integration.
                self._sync_dirs[dest] = _DIR_TO_VEGA

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        ids: set[str] = set()
        for alert in job_case.case_detail.alerts or []:
            ids.update(incident_ids_from_soar_alert(alert))
        return sorted(ids)

    def incident_ids_to_case_map_builder(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids or []:
                mapping[str(product_id)] = str(case_id)
        return mapping

    def modified_synced_case_ids_by_product(
        self,
        incident_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        if not self.manager or not incident_ids:
            return []
        id_map = self.incident_ids_to_case_map_builder()
        case_time = dict(sorted_modified_ids)
        results: list[tuple[str, int]] = []
        for incident_id in incident_ids:
            case_id = id_map.get(str(incident_id))
            if not case_id:
                continue
            try:
                incident = self.manager.get_incident(str(incident_id))
            except Exception as exc:
                self.logger.warn(f"Unable to fetch Vega incident {incident_id}: {exc}")
                continue
            if not incident:
                continue
            # Any fetched incident counts as modified enough to refresh the case.
            results.append((case_id, max(case_time.get(case_id, 0), self.last_run_time or 0)))
        return results

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        if not self.manager:
            return
        case_id = str(job_case.case_detail.id_)
        incident_ids = self._extract_product_ids_from_case(job_case)
        if not incident_ids:
            return
        # One Vega incident per case; use the first resolved id.
        incident: SingleJson = {}
        for incident_id in incident_ids:
            try:
                incident = self.manager.get_incident(incident_id) or {}
            except Exception as exc:
                self.logger.warn(f"Unable to fetch Vega incident {incident_id}: {exc}")
                continue
            if incident:
                break
        if not incident:
            return
        self._incident_by_case[case_id] = incident
        signals_in_case = len(job_case.case_detail.alerts or [])
        try:
            total_signals = int(incident.get("alertsCount") or signals_in_case)
        except (TypeError, ValueError):
            total_signals = signals_in_case

        self._sync_case_title(job_case, incident)
        self._sync_case_description(job_case, incident)
        self._sync_case_priority(job_case, incident)
        self._sync_case_insight(job_case, incident, signals_in_case, total_signals)
        self._sync_case_tags(job_case, incident)

        status = str(incident.get("userStatus") or "").strip().upper()
        incident_key = str(incident.get("id") or incident_ids[0])
        product = SimpleNamespace(**dict(incident), id=incident_key, comments=list(incident.get("comments") or []))
        mapping: dict[str, Any] = {}
        for alert in job_case.case_detail.alerts or []:
            alert_id = getattr(alert, "identifier", None) or getattr(alert, "id", None)
            if not alert_id:
                continue
            mapping[incident_key] = alert
            job_case.alert_metadata[str(alert_id)] = SyncMetadata(
                status=status,
                assignee="",
                incident_number=incident_key,
                closure_reason="",
                determination=str(incident.get("verdict") or ""),
            )
        job_case.product_ids_from_secops_alerts = mapping
        try:
            job_case.add_product_incident(product, product_key="id")
        except Exception as exc:
            self.logger.warn(f"Unable to attach Vega incident to case {case_id}: {exc}")

    def _sync_case_title(self, job_case: JobCase, incident: SingleJson) -> None:
        title = incident_case_title(incident)
        current = str(getattr(job_case.case_detail, "title", None) or getattr(job_case.case_detail, "name", None) or "")
        if not title or title == current:
            return
        try:
            rename_case(self.soar_job, int(job_case.case_detail.id_), title)
            self.logger.info(f"Renamed case {job_case.case_detail.id_} to {title!r}.")
        except Exception as exc:
            self.logger.warn(f"Unable to rename case {job_case.case_detail.id_}: {exc}")

    def _sync_case_description(self, job_case: JobCase, incident: SingleJson) -> None:
        description = str(incident.get("incidentSummary") or "").strip()
        if not description:
            return
        current = str(getattr(job_case.case_detail, "description", None) or "").strip()
        if description == current:
            return
        case_id = int(job_case.case_detail.id_)
        try:
            change_case_description(self.soar_job, case_id, description)
            self.logger.info(f"Updated description on case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to set description on case {case_id}: {exc}")

    def _sync_case_priority(self, job_case: JobCase, incident: SingleJson) -> None:
        severity = record_severity(incident)
        priority = alert_priority(severity)
        # Map numeric priority to SecOps priority label when change_case_priority expects a string.
        priority_name = {
            100: "Critical",
            80: "High",
            60: "Medium",
            40: "Low",
        }.get(int(priority), "Medium")
        case_id = str(job_case.case_detail.id_)
        alerts = list(job_case.case_detail.alerts or [])
        alert_identifier = getattr(alerts[0], "identifier", None) if alerts else None
        try:
            if hasattr(self.soar_job, "change_case_priority") and alert_identifier:
                self.soar_job.change_case_priority(
                    case_id=case_id,
                    priority=priority_name,
                    alert_identifier=alert_identifier,
                )
            else:
                self.sync_severity_to_case(
                    str(alert_identifier or ""),
                    str(getattr(alerts[0], "name", "") if alerts else ""),
                    case_id,
                    priority_name,
                )
        except Exception as exc:
            self.logger.warn(f"Unable to set priority on case {case_id}: {exc}")

    def _sync_case_insight(
        self,
        job_case: JobCase,
        incident: SingleJson,
        signals_in_case: int,
        total_signals: int,
    ) -> None:
        insight = build_incident_insight(
            incident,
            signals_in_case=signals_in_case,
            total_signals=total_signals,
        )
        case_id = int(job_case.case_detail.id_)
        try:
            from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType

            existing = []
            if hasattr(self.soar_job, "get_case_insights"):
                existing = self.soar_job.get_case_insights(case_id) or []
            for item in existing:
                body = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
                if body == insight:
                    return
            self.soar_job.create_case_insight_internal(
                case_id,
                None,
                "Vega Incident",
                insight,
                str(incident.get("id") or ""),
                InsightSeverity.INFO,
                InsightType.General,
            )
            self.logger.info(f"Wrote Vega insight on case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to write insight on case {case_id}: {exc}")

    def _sync_case_tags(self, job_case: JobCase, incident: SingleJson) -> None:
        tags = [tag for tag in collect_label_tags(incident) if tag]
        if constants.SYNC_ALERTS_TAG not in tags:
            tags.append(constants.SYNC_ALERTS_TAG)
        if not tags:
            return
        case_id = int(job_case.case_detail.id_)
        existing = {
            str(tag.get("displayName") or tag)
            for tag in (getattr(job_case.case_detail, "tags", None) or [])
            if tag
        }
        to_add = [tag for tag in tags if tag not in existing]
        if not to_add:
            return
        try:
            add_tags_to_case_in_bulk(self.soar_job, [case_id], to_add)
            self.logger.info(f"Added tags {to_add} to case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to add tags on case {case_id}: {exc}")

    def is_alert_and_product_closed(self, job_case: JobCase, product: Any) -> bool:
        incident = product if isinstance(product, dict) else {}
        status = str(incident.get("userStatus") or "").strip().upper()
        product_closed = status == constants.SYNC_RESOLVED_STATUS
        case_closed = getattr(job_case.case_detail, "status", None) == CaseDataStatus.CLOSED
        return bool(product_closed and case_closed)

    def sync_status(self, job_case: JobCase) -> None:
        direction = self._sync_dirs.get("status", _DIR_BIDI)
        if direction == _DIR_NONE or not self.manager:
            return
        case_id = str(job_case.case_detail.id_)
        incident = self._incident_by_case.get(case_id) or {}
        incident_id = str(incident.get("id") or "").strip()
        if not incident_id:
            ids = self._extract_product_ids_from_case(job_case)
            incident_id = ids[0] if ids else ""
        if not incident_id:
            return
        vega_status = str(incident.get("userStatus") or "").strip().upper()
        case_closed = getattr(job_case.case_detail, "status", None) == CaseDataStatus.CLOSED

        if direction in {_DIR_BIDI, _DIR_TO_SECOPS}:
            if vega_status == constants.SYNC_RESOLVED_STATUS and not case_closed:
                self._close_case(job_case, "Resolved in Vega")
            elif vega_status and vega_status != constants.SYNC_RESOLVED_STATUS and case_closed:
                self._reopen_case(job_case)

        if direction in {_DIR_BIDI, _DIR_TO_VEGA} and case_closed and vega_status != constants.SYNC_RESOLVED_STATUS:
            try:
                self.manager.resolve_incidents([incident_id])
                self.logger.info(f"Resolved Vega incident {incident_id} from closed case {case_id}.")
            except Exception as exc:
                self.logger.warn(f"Unable to resolve Vega incident {incident_id}: {exc}")

    def _close_case(self, job_case: JobCase, comment: str) -> None:
        case_id = str(job_case.case_detail.id_)
        try:
            self.soar_job.close_case(
                root_cause="Resolved in Vega",
                comment=comment,
                reason="Resolved in Vega",
                case_id=case_id,
                alert_id=None,
            )
            self.logger.info(f"Closed SecOps case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to close case {case_id}: {exc}")

    def _reopen_case(self, job_case: JobCase) -> None:
        case_id = str(job_case.case_detail.id_)
        try:
            if hasattr(self.soar_job, "reopen_case"):
                self.soar_job.reopen_case(case_id)
            else:
                self.logger.warn(f"reopen_case not available on this SecOps build for case {case_id}.")
                return
            self.logger.info(f"Reopened SecOps case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to reopen case {case_id}: {exc}")

    def sync_comments(self, job_case: JobCase) -> None:
        direction = self._sync_dirs.get("comments", _DIR_BIDI)
        if direction == _DIR_NONE or not self.manager:
            return
        case_id = str(job_case.case_detail.id_)
        incident = self._incident_by_case.get(case_id) or {}
        if not incident:
            return
        result = self.get_comments_to_sync(
            job_case,
            product_comment_prefix=_COMMENT_PREFIX_VEGA,
            case_comment_prefix=_COMMENT_PREFIX_SECOPS,
            product_comment_key="text",
            product_incident_key="id",
        )
        if direction in {_DIR_BIDI, _DIR_TO_SECOPS} and result.comments_to_add_to_case:
            self.sync_product_comments_to_case(int(case_id), result.comments_to_add_to_case)
        if direction in {_DIR_BIDI, _DIR_TO_VEGA} and result.comments_to_add_to_product:
            self.sync_case_comments_to_product(job_case, result.comments_to_add_to_product)

    def sync_case_comments_to_product(self, job_case: JobCase, comments: list[str]) -> None:
        if not self.manager or not comments:
            return
        case_id = str(job_case.case_detail.id_)
        incident = self._incident_by_case.get(case_id) or {}
        incident_id = str(incident.get("id") or "").strip()
        if not incident_id:
            return
        for comment in comments:
            text = str(comment or "").strip()
            if not text:
                continue
            if not text.startswith(_COMMENT_PREFIX_SECOPS):
                text = f"{_COMMENT_PREFIX_SECOPS} {text}"
            try:
                self.manager.update_incidents(
                    {
                        "incidentIds": [incident_id],
                        "comments": [{"text": text}],
                    }
                )
            except Exception as exc:
                self.logger.warn(f"Unable to push comment to Vega incident {incident_id}: {exc}")

    def sync_tags(self, job_case: JobCase) -> None:
        # Tags are applied in map_product_data_to_case from Vega labels.
        return

    def sync_severity(self, job_case: JobCase) -> None:
        # Priority is applied in map_product_data_to_case from Vega severity.
        return

    def sync_assignee(self, job_case: JobCase) -> None:
        return


def main() -> None:
    SyncAlerts().start()


if __name__ == "__main__":
    main()
