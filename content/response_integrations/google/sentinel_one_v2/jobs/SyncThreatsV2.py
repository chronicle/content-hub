from __future__ import annotations

from collections import defaultdict
import datetime
import itertools
from json import JSONDecodeError
import re
from typing import TYPE_CHECKING, Any, Callable

import requests
from requests.exceptions import HTTPError

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, convert_unixtime_to_datetime

from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.base.utils import is_native, merge_ids_by_timestamp
from TIPCommon.data_models import CaseDataStatus
from TIPCommon.rest.soar_api import get_case_overview_details
from sentinel_one_v2.core import constants
from sentinel_one_v2.core.datamodels import ThreatNote
from sentinel_one_v2.core.exceptions import SentinelOneV2Error, SentinelOneV2ManagerError
from sentinel_one_v2.core.SentinelOneV2Factory import API_VERSION_2_1, SentinelOneV2ManagerFactory
from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import NoReturn
    from sentinel_one_v2.core.datamodelsV2 import Threat


class SyncThreatsV2(BaseSyncJob[SentinelOneV2ManagerV2]):
    """Job that synchronizes Threats between Google SecOps and SentinelOne V2."""

    def __init__(self) -> None:
        """Initializes the SyncThreatsV2 job configuration."""
        super().__init__(
            job_name=constants.SYNC_THREATS_SCRIPT_NAME,
            context_identifier=constants.SYNC_THREATS_IDENTIFIER,
            tags_identifiers=[constants.SENTINELONE_THREAT_TAG],
        )
        self.sync_limit: int = constants.THREATS_CASES_SYNC_LIMIT
        self.manager: SentinelOneV2ManagerV2 | None = None
        self.threat_cache: dict[str, Threat] = {}
        self._notes_cache: dict[str, list[ThreatNote]] = {}
        self._case_details_cache: dict[str, Any] = {}
        self.threats_with_new_notes: set[str] = set()
        self.threats_native_timestamps: dict[str, int] = {}
        self._latest_checked_time: int = 0

    def _init_api_clients(self) -> None:
        """Initializes the SentinelOne V2 API client."""
        self.manager = SentinelOneV2ManagerFactory(API_VERSION_2_1).get_manager(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
            logger=self.logger,
        )

    def _retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Retries a function call once upon connection failure."""
        try:
            return func(*args, **kwargs)
        except (requests.exceptions.ConnectionError, SentinelOneV2ManagerError) as err:
            self.logger.error(f"Connection/API error: {err}")
            self.logger.info("Re-initializing client and retrying...")
            self._init_api_clients()
            return func(*args, **kwargs)

    def _is_valid_s1_id(self, val: Any) -> bool:
        """Checks if the value is a valid numeric S1 Threat ID."""
        if not val:
            return False

        val_str: str = str(val).strip()
        if not val_str.isdigit():
            return False

        return len(val_str) >= constants.MIN_THREAT_ID_LENGTH

    def _get_alert_product_id(self, alert: Any) -> str | None:
        """Extracts the SentinelOne ID from an alert's ticket_id or context."""
        if self._is_valid_s1_id(alert.ticket_id):
            return str(alert.ticket_id)

        if alert.alert_group_identifier:
            context_val: str | None = self.soar_job.get_context_property(
                constants.THREATS_ENTITY_TYPE,
                alert.alert_group_identifier,
                constants.THREAT_ID_CONTEXT_KEY
            )
            if self._is_valid_s1_id(context_val):
                return str(context_val)

        return None

    def get_product_ids_from_case_alerts(self, job_case: JobCase) -> dict[str, Any]:
        """Extracts SentinelOne Threat IDs from the case alerts."""
        product_ids_to_alert_mapping: dict[str, Any] = {}
        for alert in job_case.case_detail.alerts:
            found_id: str | None = self._get_alert_product_id(alert)

            if found_id:
                product_ids_to_alert_mapping[found_id] = alert
            else:
                self.logger.info(
                    f"SKIPPING Alert {alert.identifier}: No valid S1 ID found."
                )

        return product_ids_to_alert_mapping

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Returns a sorted list of unique SentinelOne Threat IDs in the case."""
        mapping: dict[str, Any] = self.get_product_ids_from_case_alerts(job_case)
        return sorted(list(mapping.keys()))

    def _get_cases_to_sync(self) -> list[JobCase]:
        """Fetches and prepares the list of cases to be synced based on modification
        timestamps and tags, handling merged cases cleanly.

        Returns:
            list[JobCase]: A list of JobCase objects that are prepared for synchronization.
        """
        self._case_details_cache = {}
        cases_by_modified_timestamp = self._get_case_ids_by_timestamp()
        modified_synced_case_ids = self._get_case_ids_by_timestamp(
            list(self.processed_items)
        )
        sorted_modified_ids = merge_ids_by_timestamp(
            cases_by_modified_timestamp,
            modified_synced_case_ids,
        )

        if not is_native(self.modified_synced_case_ids_by_product):
            synced_incident_ids: Iterator[str] = itertools.chain.from_iterable(
                self.processed_items.values()
            )
            modified_synced_case_ids_by_product = (
                self.modified_synced_case_ids_by_product(
                    synced_incident_ids,
                    sorted_modified_ids,
                )
            )
            sorted_modified_ids = merge_ids_by_timestamp(
                sorted_modified_ids,
                modified_synced_case_ids_by_product,
            )
        sorted_modified_ids.sort(key=lambda x: x[1])

        potential_cases = sorted_modified_ids[: self.sync_limit]
        return self._prepare_potential_cases(potential_cases)

    def _reconcile_processed_items(
        self,
        active_threat_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> None:
        """Reconciles processed_items for active threats, refreshing modified and fallback cases."""
        for case_id, _ in sorted_modified_ids[: self.sync_limit]:
            if str(case_id) not in self._case_details_cache:
                self._refresh_tracked_case(case_id)

        threat_to_case_map = self.threat_ids_to_case_map_builder()
        has_unmapped_or_stale_threat = False

        for threat_id in active_threat_ids:
            case_id = threat_to_case_map.get(threat_id)
            if (
                case_id
                and str(case_id) not in self._case_details_cache
                and (
                    case_id in self.processed_items
                    or str(case_id) in self.processed_items
                )
            ):
                self._refresh_tracked_case(case_id)

            tracked_threats = (
                self.processed_items.get(case_id)
                or self.processed_items.get(str(case_id))
                or []
            )
            if not case_id or threat_id not in {str(t) for t in tracked_threats}:
                has_unmapped_or_stale_threat = True

        if has_unmapped_or_stale_threat:
            for case_id in list(self.processed_items):
                if (
                    str(case_id) not in self._case_details_cache
                    and (
                        case_id in self.processed_items
                        or str(case_id) in self.processed_items
                    )
                ):
                    self._refresh_tracked_case(case_id)

    def _refresh_tracked_case(self, case_id: str | int) -> None:
        """Fetches and caches a tracked case, updating or purging its processed_items entry."""
        case_details = self._fetch_case_overview_details(case_id)
        if not case_details:
            return

        self._case_details_cache[str(case_id)] = case_details
        job_case = JobCase(case_detail=case_details, modification_time=0)
        incident_ids = self._extract_product_ids_from_case(job_case)

        self._remove_case_from_processed_items(case_id)
        if incident_ids:
            self.processed_items[case_id] = incident_ids
            self._reassign_claimed_threats(case_id, incident_ids)

    def _prepare_potential_cases(
        self,
        potential_cases: list[tuple[str, int]],
    ) -> list[JobCase]:
        """Fetches details for potential cases and builds JobCase instances within alert limits."""
        final_prepared_cases: list[JobCase] = []
        final_prepared_ids: list[tuple[str, int]] = []
        total_alerts_accumulated: int = 0

        for case_id, modification_time in potential_cases:
            case_details = self._case_details_cache.get(
                str(case_id)
            ) or self._fetch_case_overview_details(case_id)
            if not case_details:
                continue

            alert_count = len(case_details.alerts)
            if self._should_break_on_alert_limit(
                case_id, alert_count, total_alerts_accumulated
            ):
                break

            case_details.alerts = list(reversed(case_details.alerts))
            total_alerts_accumulated += alert_count
            job_case = JobCase(
                case_detail=case_details, modification_time=modification_time
            )
            incident_ids = self._extract_product_ids_from_case(job_case)

            self._remove_case_from_processed_items(case_id)
            if incident_ids:
                self.processed_items[case_id] = incident_ids
                self._reassign_claimed_threats(case_id, incident_ids)
                final_prepared_cases.append(job_case)
                final_prepared_ids.append((case_id, modification_time))

        self.sorted_modified_ids = final_prepared_ids
        return final_prepared_cases

    def _should_break_on_alert_limit(
        self,
        case_id: str | int,
        alert_count: int,
        total_alerts_accumulated: int,
    ) -> bool:
        """Checks if adding the case alerts exceeds product_alerts_limit."""
        if (
            not self.product_alerts_limit
            or total_alerts_accumulated + alert_count <= self.product_alerts_limit
        ):
            return False

        if total_alerts_accumulated == 0:
            self.logger.info(
                f"Case {case_id} has {alert_count} alerts, exceeding "
                f"the limit ({self.product_alerts_limit}) alone. "
                "Processing anyway to ensure progress."
            )
            return False

        self.logger.info(
            "Alert limit reached "
            f"({total_alerts_accumulated}/{self.product_alerts_limit}). "
            f"Skipping case {case_id} with {alert_count} alerts for next run."
        )
        return True

    def _fetch_case_overview_details(self, case_id: str | int) -> Any | None:
        """Fetches case overview details from SecOps and removes stale cases on failure."""
        try:
            case_details = get_case_overview_details(
                self.soar_job,
                case_id,
                case_expand=["tags"],
                alert_expand=["ClosureDetails"],
            )
            if not case_details or not case_details.id_:
                self.logger.info(
                    f"Could not retrieve details for case {case_id}. Skipping."
                )
                self._remove_case_from_processed_items(case_id)
                return None

            return case_details

        except (JSONDecodeError, HTTPError):
            self.logger.info(
                f"Could not retrieve details for case {case_id}. Skipping."
            )
            self._remove_case_from_processed_items(case_id)
            return None

    def _remove_case_from_processed_items(self, case_id: str | int) -> None:
        """Removes a case ID from processed_items if present."""
        self.processed_items.pop(case_id, None)
        self.processed_items.pop(str(case_id), None)

    def _reassign_claimed_threats(
        self,
        current_case_id: str,
        claimed_threat_ids: list[str],
    ) -> None:
        """Reassigns claimed threat IDs and cleans up stale cases from processed_items."""
        if not claimed_threat_ids:
            return

        claimed_set: set[str] = {str(t) for t in claimed_threat_ids}
        current_case_id_str = str(current_case_id)
        other_cases: list[str] = [
            cid for cid in self.processed_items if str(cid) != current_case_id_str
        ]
        for other_case_id in other_cases:
            remaining_ids: list[str] = [
                tid
                for tid in self.processed_items[other_case_id]
                if str(tid) not in claimed_set
            ]
            if remaining_ids:
                self.processed_items[other_case_id] = remaining_ids
            else:
                del self.processed_items[other_case_id]

    def threat_ids_to_case_map_builder(self) -> dict[str, str]:
        """Builds a map of {ThreatID: CaseID} from processed items."""
        threat_ids_to_case_map: dict[str, str] = {}
        for case_id, threat_ids in self.processed_items.items():
            for threat_id in threat_ids:
                threat_ids_to_case_map[threat_id] = case_id
        return threat_ids_to_case_map

    def modified_synced_case_ids_by_product(
        self,
        threat_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]]
    ) -> list[tuple[str, int]]:
        """
        Identifies cases that require synchronization based on S1 updates
        and SecOps modifications.
        """
        threat_ids_list = list(threat_ids)
        valid_threat_ids: list[str] = [
            tid for tid in threat_ids_list if self._is_valid_s1_id(tid)
        ]
        if not valid_threat_ids:
            return []

        threats_with_new_notes, status_modified_times = (
            self._get_activity_modified_threats(valid_threat_ids)
        )
        active_threat_ids: list[str] = list(
            threats_with_new_notes.union(set(status_modified_times.keys()))
        )

        if not active_threat_ids:
            self.logger.info(
                "No threat activities found since last run. Bypassing massive fetch."
            )
            return []

        self._reconcile_processed_items(active_threat_ids, sorted_modified_ids)
        threat_to_case_map: dict[str, str] = self.threat_ids_to_case_map_builder()
        modified_threats: list[Threat] = self._fetch_modified_threats(active_threat_ids)
        return self._map_threats_to_cases(
            modified_threats,
            threat_to_case_map,
            sorted_modified_ids,
            threats_with_new_notes,
            status_modified_times
        )

    def _fetch_modified_threats(self, threat_ids: list[str]) -> list[Threat]:
        """
        Fetches threats by ID in batches. 
        API-level time filter REMOVED to prevent hiding resolved threats.
        """
        threats: list[Threat] = []
        ids_to_fetch: list[str] = []

        for tid in threat_ids:
            if tid in self.threat_cache:
                threats.append(self.threat_cache[tid])
            else:
                ids_to_fetch.append(tid)

        if not ids_to_fetch:
            return threats

        for i in range(0, len(ids_to_fetch), constants.BATCH_SIZE):
            batch: list[str] = ids_to_fetch[i : i + constants.BATCH_SIZE]
            kwargs: dict[str, Any] = {"threat_ids": batch}

            try:
                batch_threats: list[Threat] = self._retry(
                    self.manager.get_threats_by_ids_inclusive,
                    **kwargs
                )

                for threat in batch_threats:
                    threat_id = str(threat.threat_id)
                    self.threat_cache[threat_id] = threat
                    threats.append(threat)

            except SentinelOneV2Error as e:
                self.logger.error(f"Failed IDs: {batch}")
                self.logger.error(f"Error details: {e}")

        return threats

    def _get_threat_modified_time_ms(self, threat: Threat) -> int:
        """Parses all possible SentinelOne timestamp variations to Unix milliseconds."""
        raw_threat_data: dict[str, Any] = getattr(threat, "raw_data", {})
        ts_str: str | None = (
            raw_threat_data.get("updatedAt") or
            raw_threat_data.get("resolvedAt") or
            raw_threat_data.get("createdAt") or
            getattr(threat, "created_at", None)
        )

        if ts_str:
            try:
                if "Z" in ts_str:
                    ts_str = ts_str.replace("Z", "+00:00")
                dt_obj: datetime.datetime = datetime.datetime.fromisoformat(ts_str)
                return convert_datetime_to_unix_time(dt_obj)
            except ValueError:
                self.logger.warning(f"Failed to parse threat timestamp: {ts_str}")

        return 0

    def _get_activity_modified_threats(
        self, threat_ids: list[str]
    ) -> tuple[set[str], dict[str, int]]:
        """
        Fetches recent activities to identify which threats received notes or status.
        """
        note_modified_threat_ids: set[str] = set()
        status_modified_times: dict[str, int] = {}

        if not threat_ids or getattr(self, "last_run_time", 0) <= 0:
            return note_modified_threat_ids, status_modified_times

        dt = convert_unixtime_to_datetime(self.last_run_time)
        last_run_iso = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        for i in range(0, len(threat_ids), 50):
            batch = threat_ids[i : i + 50]
            try:
                activities = self._retry(
                    self.manager.get_activities,
                    threatIds=",".join(batch),
                    createdAt__gte=last_run_iso,
                )
                self._process_activity_batch(
                    activities, note_modified_threat_ids, status_modified_times
                )
            except SentinelOneV2Error as e:
                self.logger.error(f"Failed to fetch activities for threats batch: {e}")

        return note_modified_threat_ids, status_modified_times

    def _process_activity_batch(
        self,
        activities: list[dict[str, Any]],
        note_modified_threat_ids: set[str],
        status_modified_times: dict[str, int]
    ) -> None:
        """
        Processes a chunk of activities to find valid newly added notes or status.
        """
        for activity in activities:
            activity_type: int | None = activity.get("activityType")
            tid: str | int | None = activity.get("threatId")
            if not tid:
                continue

            tid_str: str = str(tid)
            created_at: str = activity.get("createdAt", "")
            activity_time_ms: int = 0
            if created_at:
                try:
                    dt_obj: datetime.datetime = datetime.datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    activity_time_ms = convert_datetime_to_unix_time(dt_obj)
                except ValueError:
                    pass

            if activity_type in (
                constants.ACTIVITY_TYPE_INCIDENT_STATUS_CHANGE,
                constants.ACTIVITY_TYPE_ANALYST_VERDICT_CHANGE
            ):
                current_max: int = status_modified_times.get(tid_str, 0)
                if activity_time_ms > current_max:
                    status_modified_times[tid_str] = activity_time_ms

            note_data: dict[str, Any] = activity.get("data", {})
            note_text: str = note_data.get("noteDetails", "")

            if activity_type == constants.ACTIVITY_TYPE_NOTE_ADDED or note_text:
                raw_note_action: Any = note_data.get("noteAction")
                note_action: str = (
                    str(raw_note_action).lower() if raw_note_action else ""
                )

                if note_text and note_action == constants.ACTIVITY_NOTE_ACTION_ADDED:
                    note_modified_threat_ids.add(tid_str)
                    self._cache_threat_note_from_activity(
                        activity, tid_str, note_text
                    )

    def _cache_threat_note_from_activity(
        self,
        activity: dict[str, Any],
        tid_str: str,
        note_text: str,
    ) -> None:
        """Constructs and injects a ThreatNote into the execution cache."""
        try:
            created_at = activity.get("createdAt", "")
            raw_note = {
                "id": activity.get("id", ""),
                "text": note_text,
                "createdAt": created_at,
            }

            threat_note = ThreatNote(raw_data=raw_note, text=note_text)
            if tid_str not in self._notes_cache:
                self._notes_cache[tid_str] = []
            self._notes_cache[tid_str].append(threat_note)
        except (ValueError, TypeError, KeyError) as parse_e:
            self.logger.error(f"Failed to inline-parse note from activity: {parse_e}")

    def _evaluate_note_modifications(self, threat_id: str) -> tuple[bool, int]:
        """Checks if a threat has strictly new notes based on the last run time."""
        strictly_new_note: bool = False
        max_note_time: int = 0
        notes = self._fetch_notes_safe(threat_id)

        for note in notes:
            if note.text and note.text.startswith(
                constants.THREATS_SECOPS_COMMENT_PREFIX
            ):
                continue

            created_at_str: str | None = note.raw_data.get("createdAt")
            if created_at_str:
                try:
                    dt_obj: datetime.datetime = datetime.datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    note_time: int = convert_datetime_to_unix_time(dt_obj)
                    if note_time > max_note_time:
                        max_note_time = note_time

                    if note_time >= self.last_run_time:
                        strictly_new_note = True
                except ValueError:
                    continue

        return strictly_new_note, max_note_time

    def _evaluate_threat_modification(
        self,
        threat: Threat,
        has_new_note_activity: bool,
        status_activity_time_ms: int
    ) -> tuple[bool, int, int, bool]:
        """Evaluates if a threat has been modified since the last run."""
        threat_id: str = str(threat.threat_id)
        threat_mod_time_ms: int = self._get_threat_modified_time_ms(threat)
        is_threat_modified: bool = threat_mod_time_ms >= self.last_run_time

        if status_activity_time_ms >= self.last_run_time:
            is_threat_modified = True

        strictly_new_note: bool = False
        max_note_time: int = 0

        if has_new_note_activity:
            strictly_new, max_note_time = self._evaluate_note_modifications(threat_id)
            strictly_new_note = strictly_new

        is_modified_overall: bool = is_threat_modified or strictly_new_note
        is_exact_match_only = (
            (threat_mod_time_ms <= self.last_run_time) and
            (max_note_time <= self.last_run_time) and
            (status_activity_time_ms <= self.last_run_time)
        )

        return (
            is_modified_overall,
            threat_mod_time_ms,
            max_note_time,
            is_exact_match_only
        )

    def _map_threats_to_cases(
        self,
        threats: list[Threat],
        threat_to_case_map: dict[str, str],
        sorted_modified_ids: list[tuple[str, int]],
        threats_with_new_notes: set[str],
        status_modified_times: dict[str, int]
    ) -> list[tuple[str, int]]:
        """
        Maps updated threats to their cases using the Status/Activity Bypass filter.
        """
        results: list[tuple[str, int]] = []
        self.threats_with_new_notes = threats_with_new_notes

        for threat in threats:
            threat_id: str = str(threat.threat_id)
            case_id: str | None = threat_to_case_map.get(threat_id)

            if not case_id:
                continue

            status_activity_time_ms: int = status_modified_times.get(threat_id, 0)
            has_new_note_activity: bool = threat_id in threats_with_new_notes
            (
                is_modified,
                threat_mod_time_ms,
                max_note_time,
                _
            ) = self._evaluate_threat_modification(
                threat, has_new_note_activity, status_activity_time_ms
            )

            if not is_modified:
                continue

            case_time_ms: int = next(
                (t for cid, t in sorted_modified_ids if cid == case_id), 0
            )

            pure_s1_time: int = max(
                threat_mod_time_ms, max_note_time, status_activity_time_ms
            )

            latest_time: int = max(pure_s1_time, case_time_ms)
            results.append((case_id, latest_time))

        return results

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps SentinelOne Threat data to the SecOps JobCase object."""
        mapping: dict[str, Any] = self.get_product_ids_from_case_alerts(job_case)
        job_case.product_ids_from_secops_alerts = mapping

        threat_ids: list[str] = list(mapping.keys())

        if not threat_ids:
            return

        threat_details: list[Threat] = self._fetch_modified_threats(threat_ids)
        self._enrich_threats_with_notes(threat_details)
        self._attach_threats_to_case(job_case, threat_details)
        self._populate_alert_metadata(job_case, threat_details)
        self.remove_synced_data_from_db(job_case, threat_details)

    def _enrich_threats_with_notes(self, threats: list[Threat]) -> None:
        """Fetches and attaches notes to each threat object."""
        for threat in threats:
            threat_id_str: str = str(threat.threat_id)
            threat_mod_time_ms: int = self._get_threat_modified_time_ms(threat)

            is_newly_modified: bool = threat_mod_time_ms > self.last_run_time
            new_notes = getattr(self, "threats_with_new_notes", set())
            has_new_note: bool = threat_id_str in new_notes

            if is_newly_modified or has_new_note:
                notes: list[ThreatNote] = self._fetch_notes_safe(
                    threat_id_str, bypass_cache=is_newly_modified
                )
                for note in notes:
                    setattr(note, "message", getattr(note, "text", ""))
                threat.comments = notes
            else:
                threat.comments = []

    def _fetch_notes_safe(
        self, threat_id: str, bypass_cache: bool = False
    ) -> list[ThreatNote]:
        """Safely fetches notes for a threat, filtering old or empty ones."""
        if threat_id in getattr(self, "_notes_cache", {}) and not bypass_cache:
            return self._notes_cache[threat_id]

        try:
            all_notes: list[ThreatNote] = self._retry(
                self.manager.get_threat_notes_for_sync, threat_id
            )
            valid_notes: list[ThreatNote] = []

            for note in all_notes:
                if not bypass_cache and self._is_old_note(note):
                    continue

                if not note.text:
                    continue

                clean_text: str = self.strip_html_tags(note.text).strip()
                note.text = clean_text
                if clean_text:
                    valid_notes.append(note)

            self._notes_cache[threat_id] = valid_notes
            return valid_notes

        except SentinelOneV2Error as e:
            self.logger.error(f"Failed to fetch notes for Threat {threat_id}: {e}")
            return []

    def _attach_threats_to_case(self, job_case: JobCase, threats: list[Threat]) -> None:
        """Attaches threat objects to the JobCase using the product key."""
        for threat in threats:
            threat.threat_id_str = str(threat.threat_id)
            job_case.add_product_incident(
                incident=threat,
                product_key="threat_id_str"
            )

    def _populate_alert_metadata(
        self, job_case: JobCase, threats: list[Threat]
    ) -> None:
        """Sets the sync metadata (status, verdict) for each alert in the case."""
        for threat in threats:
            threat_id_str: str = str(threat.threat_id)
            alert_identifier: str | None = (
                job_case.get_alert_identifier_from_product_id(
                    product_id=threat_id_str
                )
            )

            if alert_identifier:
                current_status: str = str(threat.incident_status).lower()

                job_case.alert_metadata[alert_identifier] = SyncMetadata(
                    status=current_status,
                    severity=threat.rank,
                    incident_id=threat_id_str,
                    closure_reason=threat.analyst_verdict,
                    closure_comment=""
                )

    def remove_synced_data_from_db(
        self, job_case: JobCase, threats: list[Threat]
    ) -> None:
        """Removes synced entries from the DB if both Alert and Threat are closed."""
        case_id: str = str(job_case.case_detail.id_)

        for alert in job_case.case_detail.alerts:
            alert_s1_id: str | None = self._get_alert_product_id(alert)
            if not alert_s1_id:
                continue

            threat: Threat | None = next(
                (t for t in threats if str(t.threat_id) == alert_s1_id), None
            )
            if not threat:
                continue

            if self._should_remove_from_db(alert, threat):
                self._remove_synced_entries([(case_id, alert_s1_id)])

    def _should_remove_from_db(self, alert: Any, threat: Threat) -> bool:
        """Evaluates if both SecOps Alert and S1 Threat are fully closed."""
        is_alert_closed: bool = alert.status == constants.ALERT_CLOSE_STATUS

        resolved_status = constants.THREAT_STATUS_RESOLVED.lower()
        is_product_closed: bool = (
            str(threat.incident_status).lower() == resolved_status
        )

        return is_alert_closed and is_product_closed

    def is_alert_and_product_closed(self, job_case: JobCase, threat: Threat) -> bool:
        """Checks if both the SecOps Alert and S1 Threat are in closed state."""
        product_id: str = str(threat.threat_id)
        alert: Any = job_case.product_ids_from_secops_alerts.get(product_id)
        if not alert:
            return False

        is_alert_closed: bool = alert.status == constants.ALERT_CLOSE_STATUS

        resolved_status = constants.THREAT_STATUS_RESOLVED.lower()
        is_product_closed: bool = (
            str(threat.incident_status).lower() == resolved_status
        )

        return is_alert_closed and is_product_closed

    def _is_old_note(self, note: ThreatNote) -> bool:
        """Checks if a note was created before the last sync time."""
        if not self.last_run_time:
            return False

        created_at: str | None = note.raw_data.get("createdAt")
        if not created_at:
            return False

        try:
            created_at = created_at.replace("Z", "+00:00")
            note_dt: datetime.datetime = datetime.datetime.fromisoformat(created_at)
            note_ms: int = convert_datetime_to_unix_time(note_dt)
            return note_ms < self.last_run_time
        except (ValueError, TypeError):
            return False

    def strip_html_tags(self, text: str) -> str:
        """Removes HTML tags from the provided text."""
        if not isinstance(text, str):
            return text
        clean: re.Pattern[str] = re.compile("<.*?>")
        return re.sub(clean, "", text)

    def sync_status(self, job_case: JobCase) -> None:
        """Orchestrates bi-directional status synchronization."""
        res: Any = job_case.get_status_to_sync(constants.THREAT_STATUS_RESOLVED)
        self._sync_product_status_to_case(res, job_case)
        self._sync_case_status_to_product(res, job_case)

    def _sync_product_status_to_case(self, res: Any, job_case: JobCase) -> None:
        """Syncs SentinelOne -> SecOps status."""
        for alert, meta in res.alerts_to_close_in_soar:
            reason, root_cause = self._map_s1_verdict_to_secops(meta.closure_reason)
            closure_comment: str = (
                f"Closed via Sync. SentinelOne Threat {meta.incident_id} is Resolved. "
                f"Verdict: {meta.closure_reason or 'None'}"
            )
            self.sync_product_status_to_case(
                case_id=job_case.case_detail.id_,
                alert_id=alert.identifier,
                reason=reason,
                root_cause=root_cause,
                comment=closure_comment
            )
            self._remove_synced_entries([(job_case.case_detail.id_, meta.incident_id)])

    def _get_case_closure_reason(self, job_case: JobCase) -> str | None:
        """Helper to get case closure reason if applicable."""
        if job_case.case_detail.status != CaseDataStatus.CLOSED:
            return None
        try:
            details_list: list[dict[str, Any]] = self.soar_job.get_case_closure_details(
                [job_case.case_detail.id_]
            )
            return details_list[0].get("reason", "") if details_list else None
        except (IndexError, KeyError):
            return None

    def _sync_case_status_to_product(self, res: Any, job_case: JobCase) -> None:
        """Syncs SecOps -> SentinelOne status using grouped bulk API requests."""
        closure_requests: list[Any] = res.incidents_to_close_in_product
        if not closure_requests:
            return

        case_id: str = str(job_case.case_detail.id_)
        case_reason: str | None = self._get_case_closure_reason(job_case)
        verdict_groups: dict[str, list[str]] = defaultdict(list)
        threat_ids: list[str] = []

        for req in closure_requests:
            secops_reason: str | None = (
                case_reason if req["is_case_closed"] and case_reason else req["reason"]
            )
            target_s1_verdict: str | None = self._map_secops_reason_to_s1_verdict(
                secops_reason
            )
            threat_id: str = req["meta"].incident_id

            if target_s1_verdict:
                verdict_groups[target_s1_verdict].append(threat_id)
            threat_ids.append(threat_id)

        if threat_ids:
            self._process_status_batches(case_id, verdict_groups, threat_ids)

    def _process_status_batches(
        self, case_id: str, verdict_groups: dict[str, list[str]], threat_ids: list[str]
    ) -> None:
        """
        Handles the retry wrapper, logging, and database cleanup for grouped closures.
        """
        try:
            self._retry(self._execute_sentinelone_api_calls, verdict_groups, threat_ids)
            self._remove_synced_entries([(case_id, tid) for tid in threat_ids])
            self.logger.info(
                f"Successfully synced and cleaned up {len(threat_ids)} threats "
                f"for Case {case_id}."
            )

        except SentinelOneV2Error as error:
            self.logger.error(f"Sync failed for Case {case_id}: {error}")

    def _execute_sentinelone_api_calls(
        self, verdict_groups: dict[str, list[str]], threat_ids: list[str]
    ) -> None:
        """
        Runs the SentinelOne API calls for threats using natively available 
        manager methods.
        """

        for verdict, ids in verdict_groups.items():
            if verdict and ids:
                self.manager.update_analyst_verdict_bulk(
                    threat_ids=ids, analyst_verdict=verdict
                )
                self.logger.info(f"Updated verdict '{verdict}' for S1 Threats: {ids}")

        if threat_ids:
            self.manager.update_incident_status(
                incident_ids=threat_ids, status=constants.THREAT_STATUS_RESOLVED
            )
            self.logger.info(f"Resolved S1 Threats: {threat_ids}")

    def sync_comments(self, job_case: JobCase) -> None:
        """Orchestrates bi-directional comment synchronization."""
        job_case.case_comments = self.soar_job.fetch_case_comments(
            case_id=job_case.case_detail.id_,
            time_filter_type=constants.THREATS_COMMENTS_MODIFICATION_TIME_FILTER,
            from_timestamp=(
                self.last_run_time - constants.SYNC_COMMENTS_OFFSET_BUFFER_MS
            ),
        )

        comments_to_sync: Any = self.get_comments_to_sync(
            job_case=job_case,
            product_comment_prefix=constants.THREATS_SENTINELONE_COMMENT_PREFIX,
            case_comment_prefix=constants.THREATS_SECOPS_COMMENT_PREFIX,
            product_comment_key="text",
            product_incident_key="threat_id_str"
        )

        self.sync_product_comments_to_case(
            case_id=job_case.case_detail.id_,
            comments=comments_to_sync.product_comments_sync_to_case
        )
        self.sync_case_comments_to_product(
            job_case=job_case,
            comments=comments_to_sync.case_comments_sync_to_product
        )

    def sync_case_comments_to_product(
        self, job_case: JobCase, comments: list[str]
    ) -> None:
        """Orchestrates pushing SecOps comments to SentinelOne Threats."""
        if not comments:
            return

        target_threat_ids = self._get_target_threat_ids_for_comments(job_case)
        if not target_threat_ids:
            return

        existing_s1_comments = set()
        for threat_id in target_threat_ids:
            all_notes = self._fetch_notes_safe(threat_id, bypass_cache=True)
            for note in all_notes:
                if note.text:
                    existing_s1_comments.add(note.text.strip())

        filtered_comments = []
        for comment in comments:
            if comment.strip() in existing_s1_comments:
                continue

            filtered_comments.append(comment)

        if not filtered_comments:
            return

        self._push_comments_to_threats(target_threat_ids, filtered_comments)

    def _get_target_threat_ids_for_comments(self, job_case: JobCase) -> list[str]:
        """Returns unique SentinelOne Threat IDs that are still active/unresolved."""
        target_threat_ids: set[str] = set()

        for alert in job_case.case_detail.alerts:
            threat = getattr(alert, "incident", None)
            if threat:
                inc_status = str(getattr(threat, "incident_status", "")).lower()
                if inc_status == constants.THREAT_STATUS_RESOLVED.lower():
                    continue

                target_threat_ids.add(str(threat.threat_id))

        return list(target_threat_ids)

    def _push_comments_to_threats(
        self, threat_ids: list[str], comments: list[str]
    ) -> None:
        """Executes the API payload to append notes to multiple S1 Threats."""
        for comment in comments:
            try:
                self.manager.add_notes_to_threat(threat_ids, comment)
                preview: str = comment[:40] + "..." if len(comment) > 40 else comment

                self.logger.info(
                    f"Successfully synced comment '{preview}' "
                    f"to {len(threat_ids)} SentinelOne Threats. "
                    f"Threat IDs: {', '.join(threat_ids)}"
                )
            except SentinelOneV2Error as e:
                self.logger.error(
                    f"Failed to push comment to Target IDs: {threat_ids}. Error: {e}"
                )

    def _map_s1_verdict_to_secops(self, verdict: str) -> tuple[str, str]:
        """Maps SentinelOne verdict to SecOps reason and root cause."""
        if verdict == constants.VERDICT_TRUE_POSITIVE:
            return (
                constants.REASON_MALICIOUS,
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            )
        if verdict == constants.VERDICT_FALSE_POSITIVE:
            return (
                constants.REASON_NOT_MALICIOUS,
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            )
        return (
            constants.REASON_INCONCLUSIVE,
            CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
        )

    def _map_secops_reason_to_s1_verdict(self, reason: str) -> str | None:
        """Maps SecOps closure reason to SentinelOne verdict."""
        if not reason:
            return None

        clean_reason: str = reason.strip()
        if clean_reason == constants.REASON_MALICIOUS:
            return constants.VERDICT_TRUE_POSITIVE
        if clean_reason == constants.REASON_NOT_MALICIOUS:
            return constants.VERDICT_FALSE_POSITIVE

        return None

    def sync_severity(self, job_case: JobCase) -> None:
        pass

    def sync_assignee(self, job_case: JobCase) -> None:
        pass

    def sync_tags(self, job_case: JobCase) -> None:
        pass

def main() -> NoReturn:
    """Main entry point for the SyncThreatsV2 job."""
    SyncThreatsV2().start()


if __name__ == "__main__":
    main()
