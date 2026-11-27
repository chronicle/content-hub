"""Sync Alerts — SecOps case description + insight from Vega incident."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase
from TIPCommon.rest.custom_types import HttpMethod
from TIPCommon.rest.soar_api import (
    add_tags_to_case_in_bulk,
    change_case_description,
    get_case_insights,
    get_case_overview_details,
    validate_response,
)
from TIPCommon.rest.soar_platform_clients.api_client_factory import get_soar_client
from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi

from ..core import constants
from ..core.case_insight import (
    build_case_description,
    build_incident_insight,
    extract_signal_id_from_ticket,
    incident_ids_from_soar_alert,
)
from ..core.mapping import collect_label_tags, is_graphql_alert_id, pending_case_tags
from ..core.utils import parse_iso_timestamp
from ..core.VegaManager import VegaClientConfig, VegaManager

if TYPE_CHECKING:
    from collections.abc import Iterable

    from TIPCommon.types import SingleJson

_INSIGHT_TITLE = "Vega Incident"
# Keep merge helpers in this job file so packaging does not depend on Managers/case_dedup.py
# being present on every worker (JobsScrips can update without a Managers redeploy).
_INSTANCE_PATH_RE = re.compile(r"projects/[^/]+/locations/[^/]+/instances/[^/]+")
_SDK_CONFIG_FALLBACK_TOKENS = (
    "/projects/project/",
    "/locations/location/",
    "/instances/instance/",
)


def _can_merge_cases(primary_alerts: int, duplicate_alerts: int, max_alerts: int) -> bool:
    cap = max(0, int(max_alerts))
    if cap <= 0:
        return False
    return int(primary_alerts) + int(duplicate_alerts) <= cap


def _resolve_cases_merge_url(soar_job: Any) -> tuple[str | None, str]:
    """Build Chronicle v1beta ``cases:merge`` URL from SDK config, or ``(None, reason)``."""
    try:
        fmt = soar_job.sdk_config.one_platform_api_root_uri_format
    except AttributeError:
        return None, "sdk_config.one_platform_api_root_uri_format unavailable"
    if not fmt:
        return None, "sdk_config.one_platform_api_root_uri_format unavailable"
    try:
        base = fmt.format("v1beta")
    except Exception as exc:
        return None, f"sdk_config format failed: {exc}"
    if _INSTANCE_PATH_RE.search(base) and not any(t in base for t in _SDK_CONFIG_FALLBACK_TOKENS):
        return base.rstrip("/") + "/cases:merge", "sdk_config auto-detect"
    return None, "sdk_config missing or placeholder instance path"


def _incident_updated_ms(incident: SingleJson) -> int:
    raw = str(
        (incident or {}).get("lastUpdated")
        or (incident or {}).get("updatedAt")
        or (incident or {}).get("createdAt")
        or ""
    ).strip()
    parsed = parse_iso_timestamp(raw) if raw else None
    if not parsed:
        return 0
    return int(parsed.timestamp() * 1000)


class SyncAlerts(BaseSyncJob[VegaManager]):
    """Write case description/insight and merge duplicate Vega-tagged cases."""

    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_ALERTS_SCRIPT_NAME,
            context_identifier=constants.SYNC_ALERTS_IDENTIFIER,
            tags_identifiers=[constants.SYNC_ALERTS_TAG],
        )
        self.sync_limit = constants.CASES_SYNC_LIMIT
        # tipcommon default (30) blocks large Vega cases after small tagged cases burn the budget
        self.product_alerts_limit = 0
        self.manager: VegaManager | None = None

    def _init_api_clients(self) -> None:
        self.manager = VegaManager(
            VegaClientConfig(
                api_root=self.params.api_root,
                access_key_id=self.params.access_key_id,
                access_key=self.params.access_key,
                verify_ssl=bool(self.params.verify_ssl),
            ),
            logger_instance=self.logger,
        )

    def _max_alerts_in_case(self) -> int:
        raw = getattr(self.params, "max_alerts_in_case", None)
        try:
            value = int(raw if raw is not None else constants.MAX_ALERTS_IN_CASE_DEFAULT)
        except (TypeError, ValueError):
            value = constants.MAX_ALERTS_IN_CASE_DEFAULT
        return max(constants.MAX_ALERTS_IN_CASE_MIN, min(constants.MAX_ALERTS_IN_CASE_MAX, value))

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Incident UUID from alert ticket_id / grouping: ``Vega:incident:<uuid>``."""
        ids: set[str] = set()
        for alert in job_case.case_detail.alerts or []:
            ids.update(incident_ids_from_soar_alert(alert))
        return sorted(ids)

    def _get_cases_to_sync(self) -> list[JobCase]:
        # Merge first for the job time range; only then description/insight sync.
        self._dedupe_vega_cases()
        cases = super()._get_cases_to_sync()
        # Base job advances watermark to sorted_modified_ids[-1] after a successful
        # run (sync_limit batch). Log when more cases remain for the next tick.
        prepared = len(self.sorted_modified_ids or [])
        if prepared >= self.sync_limit:
            last_ts = self.sorted_modified_ids[-1][1] if self.sorted_modified_ids else 0
            self.logger.info(
                f"Sync batch full ({prepared}/{self.sync_limit}). "
                f"Watermark will move to {last_ts} so the next run continues "
                "with the following cases."
            )
        elif prepared:
            self.logger.info(
                f"Sync batch {prepared}/{self.sync_limit}. "
                "Watermark advances to the last case in this set."
            )
        return cases

    def modified_synced_case_ids_by_product(
        self,
        incident_ids: list[str] | Iterable[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Re-queue only when the Vega incident changed since last_run.

        Fetches incidents in batches to avoid one GraphQL call per id.

        Watermark: prefer the SecOps ``updateTime`` already on
        ``sorted_modified_ids``. For product-only hits, clamp to
        ``min(vega_updated, now)`` so a far-ahead Vega timestamp cannot jump
        the job cursor past the next SecOps batch (``sync_limit``).
        """
        if not self.manager:
            return []
        unique_ids = list(dict.fromkeys(str(item).strip() for item in incident_ids if str(item or "").strip()))
        if not unique_ids:
            return []
        id_map: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids or []:
                id_map[str(product_id)] = str(case_id)
        last_run = int(self.last_run_time or 0)
        secops_time = {str(case_id): int(ts) for case_id, ts in (sorted_modified_ids or [])}
        now_ms = int(self._cached_unix_now or 0)
        try:
            incidents = self.manager.get_incidents_by_ids(unique_ids)
        except Exception as exc:
            self.logger.warn(f"Unable to batch-fetch Vega incidents: {exc}")
            return []
        results: list[tuple[str, int]] = []
        seen_cases: set[str] = set()
        for incident_id in unique_ids:
            case_id = id_map.get(str(incident_id))
            if not case_id or case_id in seen_cases:
                continue
            incident = incidents.get(str(incident_id)) or {}
            if not incident:
                continue
            updated_ms = _incident_updated_ms(incident)
            if updated_ms <= last_run:
                continue
            seen_cases.add(case_id)
            if case_id in secops_time:
                ts = secops_time[case_id]
            elif now_ms > 0:
                ts = min(updated_ms, now_ms)
            else:
                ts = updated_ms
            # Keep cursor moving forward when we only have a product hit.
            if ts <= last_run:
                ts = last_run + 1
            results.append((case_id, ts))
        return results

    def _dedupe_vega_cases(self) -> None:
        """Priority step: merge duplicate Vega-tagged cases in the job time range.

        Scans every Vega-tagged case between ``last_run`` and now (same window as
        sync). Merges open cases that share one Vega incident id (oldest wins)
        with no comment/tag. Description/insight sync runs only after this step.
        """
        self.logger.info(
            "Vega case dedup starting (priority before description/insight sync)."
        )
        try:
            candidates = self._get_case_ids_by_timestamp()
        except Exception as exc:
            self.logger.warn(f"Vega case dedup aborted: unable to list cases in time range ({exc})")
            return

        if not candidates:
            self.logger.info("Vega case dedup: no Vega-tagged cases in job time range.")
            return

        merge_url, source = _resolve_cases_merge_url(self.soar_job)
        if not merge_url:
            self.logger.warn(f"Skip Vega case dedup: cases:merge URL unresolved ({source}).")
            return

        by_incident: dict[str, list[dict[str, Any]]] = {}
        for case_id, _update_time in candidates:
            try:
                details = get_case_overview_details(self.soar_job, case_id)
            except Exception as exc:
                self.logger.warn(f"Dedup skip case {case_id}: unable to load overview ({exc})")
                continue
            if getattr(details, "is_closed", False):
                continue
            incident_ids: set[str] = set()
            for alert in getattr(details, "alerts", None) or []:
                incident_ids.update(incident_ids_from_soar_alert(alert))
            if not incident_ids:
                continue
            row = {
                "case_id": str(case_id),
                "start_time": int(getattr(details, "creation_time_unix_time_ms", 0) or 0),
                "alert_count": len(getattr(details, "alerts", None) or []),
            }
            for incident_id in incident_ids:
                by_incident.setdefault(str(incident_id), []).append(row)

        dup_groups = {
            incident_id: rows
            for incident_id, rows in by_incident.items()
            if len({str(item["case_id"]) for item in rows}) > 1
        }
        if not dup_groups:
            self.logger.info(
                f"Vega case dedup: {len(candidates)} case(s) in range, no duplicate "
                "incident pairs. Continuing with sync."
            )
            return

        self.logger.info(
            f"Vega case dedup via {source}: {len(dup_groups)} incident(s) with "
            f"duplicate cases in time range ({len(candidates)} Vega-tagged case(s))."
        )

        max_alerts = self._max_alerts_in_case()
        merged = 0
        skipped_limit = 0
        for incident_id, rows in dup_groups.items():
            # One row per case_id (a case can appear once per incident group).
            unique_rows: dict[str, dict[str, Any]] = {}
            for row in rows:
                unique_rows.setdefault(str(row["case_id"]), row)
            ordered = sorted(unique_rows.values(), key=lambda item: int(item["start_time"]))
            if len(ordered) < 2:
                continue
            primary = ordered[0]
            primary_count = int(primary["alert_count"])
            for dup in ordered[1:]:
                if dup["case_id"] == primary["case_id"]:
                    continue
                dup_count = int(dup["alert_count"])
                if not _can_merge_cases(primary_count, dup_count, max_alerts):
                    skipped_limit += 1
                    self.logger.info(
                        f"Skip merge {dup['case_id']} → {primary['case_id']} for incident "
                        f"{incident_id}: {primary_count}+{dup_count} exceeds "
                        f"Max Alerts in Case={max_alerts}."
                    )
                    continue
                try:
                    if self._merge_cases(merge_url, primary["case_id"], dup["case_id"]):
                        merged += 1
                        primary_count += dup_count
                        self.processed_items.pop(dup["case_id"], None)
                except Exception as exc:
                    self.logger.warn(
                        f"Failed to merge case {dup['case_id']} into {primary['case_id']}: {exc}"
                    )

        if skipped_limit:
            self.logger.warn(
                f"Vega case dedup finished with {skipped_limit} unmerged pair(s) "
                f"(over Max Alerts in Case). merged={merged}. Continuing with sync."
            )
        else:
            self.logger.info(
                f"Vega case dedup done. merged={merged}. No remaining mergeable "
                "duplicates in time range. Continuing with sync."
            )

    def _merge_cases(self, merge_url: str, primary_case_id: str, duplicate_case_id: str) -> bool:
        """POST cases:merge with no comment or tag."""
        try:
            dup_id = int(duplicate_case_id)
            primary_id = int(primary_case_id)
        except (TypeError, ValueError):
            self.logger.warn(
                f"Skipping merge: non-integer case ids "
                f"(dup={duplicate_case_id!r} primary={primary_case_id!r})."
            )
            return False
        body = {"casesIds": [dup_id, primary_id], "caseToMergeWith": primary_id}
        self.logger.info(f"Merging case {duplicate_case_id} into {primary_case_id} (no comment/tag).")
        resp = self.soar_job.session.post(merge_url, json=body)
        resp.raise_for_status()
        try:
            result = resp.json() or {}
        except ValueError:
            result = {}
        errors = result.get("errors") or []
        if not bool(result.get("isRequestValid", True)) or errors:
            self.logger.warn(
                f"cases.merge failed for {duplicate_case_id} → {primary_case_id}: {errors or result}"
            )
            return False
        return True

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        if not self.manager:
            return
        # SecOps rejects description/insight writes on closed cases (400 / errorCode 2000).
        if job_case.case_detail.is_closed:
            self.logger.info(
                f"Skipping description/insight on closed case {job_case.case_detail.id_}."
            )
            return
        incident_ids = self._extract_product_ids_from_case(job_case)
        if not incident_ids:
            return
        try:
            fetched = self.manager.get_incidents_by_ids(incident_ids)
        except Exception as exc:
            self.logger.warn(f"Unable to batch-fetch Vega incidents for case sync: {exc}")
            fetched = {}
        incident: SingleJson = {}
        for incident_id in incident_ids:
            incident = fetched.get(str(incident_id)) or {}
            if incident:
                break
        if not incident:
            return
        signals_in_case = len(job_case.case_detail.alerts or [])
        try:
            total_signals = int(incident.get("alertsCount") or signals_in_case)
        except (TypeError, ValueError):
            total_signals = signals_in_case
        self._sync_case_description(job_case, incident)
        self._sync_case_insight(job_case, incident, signals_in_case, total_signals)
        self._sync_vega_label_tags(job_case, incident)

    def _case_tag_names(self, job_case: JobCase) -> list[str]:
        names: list[str] = []
        for raw in getattr(job_case.case_detail, "tags", None) or []:
            if isinstance(raw, dict):
                name = str(raw.get("name") or raw.get("displayName") or raw.get("Name") or "").strip()
            else:
                name = str(getattr(raw, "name", None) or getattr(raw, "displayName", None) or raw).strip()
            if name:
                names.append(name)
        return names

    def _signal_ids_for_case(self, job_case: JobCase, incident: SingleJson) -> list[str]:
        """Vega alert ids for signals already on this SecOps case (+ incident stubs)."""
        ids: list[str] = []
        seen: set[str] = set()

        def _add(value: str) -> None:
            text = str(value or "").strip()
            if text and text not in seen:
                seen.add(text)
                ids.append(text)

        for alert in job_case.case_detail.alerts or []:
            for candidate in (
                getattr(alert, "ticket_id", None),
                getattr(alert, "display_id", None),
                getattr(alert, "identifier", None),
            ):
                signal_id = extract_signal_id_from_ticket(str(candidate or ""))
                if signal_id:
                    _add(signal_id)
        for stub in incident.get("alerts") or []:
            if isinstance(stub, dict):
                _add(str(stub.get("alertId") or stub.get("id") or ""))
        return ids

    def _fetch_alert_records(self, alert_ids: list[str]) -> list[SingleJson]:
        if not self.manager or not alert_ids:
            return []
        graphql_ids = [item for item in alert_ids if is_graphql_alert_id(item)]
        other_ids = [item for item in alert_ids if item not in set(graphql_ids)]
        records: list[SingleJson] = []
        batch = max(1, int(constants.ALERT_ID_LOOKUP_BATCH))
        from_ts = constants.ALERT_ID_LOOKUP_FROM

        def _lookup(ids: list[str], *, use_alert_ids: bool) -> None:
            for index in range(0, len(ids), batch):
                chunk = ids[index : index + batch]
                variables: SingleJson = {
                    "from": from_ts,
                    "updatedFrom": from_ts,
                }
                if use_alert_ids:
                    variables["alertIds"] = chunk
                else:
                    variables["vegaAlertIds"] = chunk
                try:
                    rows = self.manager.get_alerts(
                        variables,
                        max_records=len(chunk),
                        page_size=len(chunk),
                    )
                except Exception as exc:
                    self.logger.warn(
                        f"Unable to fetch Vega alert labels for {len(chunk)} id(s): {exc}"
                    )
                    continue
                records.extend(row for row in (rows or []) if isinstance(row, dict))

        _lookup(graphql_ids, use_alert_ids=True)
        _lookup(other_ids, use_alert_ids=False)
        return records

    def _sync_vega_label_tags(self, job_case: JobCase, incident: SingleJson) -> None:
        """Create/assign SecOps case tags from Vega incident + alert labels."""
        alert_ids = self._signal_ids_for_case(job_case, incident)
        alert_records = self._fetch_alert_records(alert_ids)
        wanted = collect_label_tags(incident, *alert_records)
        # Keep the integration tag so SyncAlerts still finds the case next run.
        if constants.SYNC_ALERTS_TAG not in {name.casefold() for name in wanted}:
            wanted = [constants.SYNC_ALERTS_TAG, *wanted]
        pending = pending_case_tags(wanted, self._case_tag_names(job_case))
        if not pending:
            self.logger.info(
                f"No new Vega label tags for case {job_case.case_detail.id_}."
            )
            return
        case_id = int(job_case.case_detail.id_)
        try:
            add_tags_to_case_in_bulk(self.soar_job, [case_id], pending)
            self.logger.info(
                f"Added {len(pending)} Vega label tag(s) on case {case_id}: {', '.join(pending)}."
            )
        except Exception as exc:
            self.logger.warn(f"Unable to add Vega label tags on case {case_id}: {exc}")

    def _update_case_description(self, case_id: int, description: str) -> None:
        client = get_soar_client(self.soar_job)
        if isinstance(client, OnePlatformSoarApi):
            response = client._make_request(
                HttpMethod.PATCH,
                f"/cases/{case_id}",
                params={"updateMask": "description"},
                json_payload={"description": description},
            )
            validate_response(response, validate_json=False)
            return
        change_case_description(self.soar_job, case_id, description)

    def _sync_case_description(self, job_case: JobCase, incident: SingleJson) -> None:
        description = build_case_description(incident)
        if not description:
            return
        current = str(getattr(job_case.case_detail, "description", None) or "").strip()
        if description == current:
            return
        case_id = int(job_case.case_detail.id_)
        try:
            self._update_case_description(case_id, description)
            self.logger.info(f"Updated description on case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to set description on case {case_id}: {exc}")

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
        alerts = list(job_case.case_detail.alerts or [])
        # Pin to one alert — None fans the insight out under every alert on the case.
        alert_identifier = getattr(alerts[0], "identifier", None) if alerts else None
        try:
            from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType

            for item in get_case_insights(self.soar_job, case_id) or []:
                title = item.get("title") if isinstance(item, dict) else getattr(item, "title", None)
                if title == _INSIGHT_TITLE:
                    self.logger.info(f"Vega insight already on case {case_id}; skipping.")
                    return
            self.soar_job.create_case_insight_internal(
                str(case_id),
                alert_identifier,
                constants.INTEGRATION_NAME,
                _INSIGHT_TITLE,
                insight,
                "",
                InsightSeverity.INFO,
                InsightType.General,
            )
            self.logger.info(f"Wrote Vega insight on case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to write insight on case {case_id}: {exc}")

    def is_alert_and_product_closed(self, job_case: JobCase, product: Any) -> bool:
        return False


def main() -> None:
    SyncAlerts().start()


if __name__ == "__main__":
    main()
