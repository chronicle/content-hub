from __future__ import annotations

import datetime
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from requests.exceptions import ConnectionError as RequestsConnectionError

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import CaseDataStatus
from sentinel_one_v2.core import constants
from sentinel_one_v2.core.exceptions import SentinelOneV2ManagerError
from sentinel_one_v2.core.SentinelOneV2Factory import API_VERSION_2_1, SentinelOneV2ManagerFactory
from sentinel_one_v2.core.SentinelOneV2ManagerV2 import SentinelOneV2ManagerV2

if TYPE_CHECKING:
    from typing import Any, NoReturn

    from collections.abc import Callable

    from TIPCommon.types import SingleJson

    from sentinel_one_v2.core.datamodelsV2 import Alert


class SyncAlertsV2(BaseSyncJob[SentinelOneV2ManagerV2]):
    """Syncs alerts between Google SecOps and SentinelOne V2.1."""

    def __init__(self) -> None:
        """Initializes the job."""
        super().__init__(
            job_name=constants.SYNC_ALERTS_JOB_NAME,
            context_identifier=constants.SYNC_ALERTS_CONTEXT_IDENTIFIER,
            tags_identifiers=[constants.SECOPS_CASE_TAG],
        )
        self.sync_limit: int = constants.CASES_SYNC_LIMIT
        self.manager: SentinelOneV2ManagerV2 | None = None
        self.alert_cache: dict[str, Alert] = {}

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
        """Retries a function call with exponential backoff upon connection failure."""

        for attempt in range(constants.MAX_RETRIES + 1):
            try:
                if attempt > constants.INITIAL_ATTEMPT:
                    self._init_api_clients()

                return func(*args, **kwargs)

            except (RequestsConnectionError, SentinelOneV2ManagerError) as error:
                is_last_attempt = attempt == constants.MAX_RETRIES

                if is_last_attempt:
                    error_msg = (
                        f"Max retries ({constants.MAX_RETRIES}) reached for "
                        f"{func.__name__}. Error: {error}"
                    )
                    self.logger.error(error_msg)
                    raise SentinelOneV2ManagerError(error_msg) from error

                delay: int = constants.RETRY_INITIAL_DELAY * (
                    constants.RETRY_BACKOFF_FACTOR**attempt
                )

                self.logger.error(
                    f"API Error in {func.__name__}: {error}. "
                    f"Retrying in {delay}s..."
                )

                time.sleep(delay)

        raise SentinelOneV2ManagerError(
            f"Unexpected retry flow exit for {func.__name__}"
        )

    def _is_valid_s1_id(self, value: Any) -> bool:
        """Checks if a value is a valid numeric S1 ID."""
        if not value:
            return False

        value_string: str = str(value).strip()
        min_len = constants.MIN_ALERT_ID_LENGTH

        return value_string.isdigit() and len(value_string) >= min_len

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Returns sorted list of unique SentinelOne IDs in the case."""
        return sorted(self.get_product_ids_from_case_alerts(job_case).keys())

    def modified_synced_case_ids_by_product(
        self,
        alert_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]]
    ) -> list[tuple[str, int]]:
        """Identifies cases requiring sync based on S1 updates."""
        valid_ids: list[str] = [tid for tid in alert_ids if self._is_valid_s1_id(tid)]
        if not valid_ids:
            return []

        updates: list[Alert] = self._fetch_product_alerts(valid_ids)
        if not updates:
            return []

        modified_cases: list[tuple[str, int]] = []
        alert_to_case_map: dict[str, str] = self._build_alert_lookup()
        case_time_map = dict(sorted_modified_ids)

        for alert in updates:
            case_id: str | None = alert_to_case_map.get(str(alert.alert_id))
            if not case_id:
                continue

            alert_ts: int = self._extract_alert_timestamp_ms(alert)
            s1_status: str = str(getattr(alert, "incident_status", "")).lower()
            is_resolved = s1_status == constants.SENTINELONE_RESOLVED.lower()

            if alert_ts <= self.last_run_time and not is_resolved:
                continue

            alert_timestamp = self._extract_alert_timestamp_ms(alert)
            case_timestamp = case_time_map.get(case_id, 0)
            final_ts: int = max(alert_timestamp, case_timestamp)
            modified_cases.append((case_id, final_ts))

        return modified_cases

    def _build_alert_lookup(self) -> dict[str, str]:
        """Builds a map of {AlertID: CaseID} from processed items."""
        return {
            alert_id: case_id
            for case_id, alert_ids in self.processed_items.items()
            for alert_id in alert_ids
        }

    def _fetch_product_alerts(self, alert_ids: list[str]) -> list[Alert]:
        """Fetches alerts from S1 in batches using retry logic."""
        results: list[Alert] = []
        ids_to_fetch: list[str] = []
        chunk_size: int = constants.FETCH_ALERTS_CHUNK_SIZE

        for aid in alert_ids:
            if aid in self.alert_cache:
                results.append(self.alert_cache[aid])
            else:
                ids_to_fetch.append(aid)

        if not ids_to_fetch:
            return results

        if not self.manager:
            self._init_api_clients()

        for i in range(0, len(ids_to_fetch), chunk_size):
            batch: list[str] = ids_to_fetch[i: i + chunk_size]
            try:
                batch_res: list[Alert] = self._retry(
                    self.manager.get_cloud_detection_alerts,
                    alert_ids=batch,
                )
                self.alert_cache.update({str(a.alert_id): a for a in batch_res})
                results.extend(batch_res)

            except (RequestsConnectionError, SentinelOneV2ManagerError) as error:
                self.logger.error(f"Failed to fetch batch starting at {i}: {error}")

        return results

    def _extract_alert_timestamp_ms(self, alert: Alert) -> int:
        """Parses the alert timestamp to Unix milliseconds."""
        ts_str: str | None = (
            getattr(alert, "updated_at", None) or
            getattr(alert, "created_at", None)
        )
        if ts_str:
            try:
                dt_obj = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return convert_datetime_to_unix_time(dt_obj)

            except ValueError:
                self.logger.warn(f"Failed to parse timestamp string: {ts_str}")

        return self.last_run_time

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps S1 data to SecOps case using local mapping."""
        ids_map: SingleJson = self.get_product_ids_from_case_alerts(job_case)
        job_case.product_ids_from_secops_alerts = ids_map

        if not ids_map:
            return

        s1_alerts: list[Alert] = self._fetch_product_alerts(list(ids_map.keys()))
        self._map_alerts_to_metadata(job_case, s1_alerts, ids_map)
        self.remove_synced_data_from_db(job_case, s1_alerts)

    def get_product_ids_from_case_alerts(self, job_case: JobCase) -> SingleJson:
        """Extracts Sentinelone alerts IDs from case alerts."""
        mapping: SingleJson = {}
        for alert in job_case.case_detail.alerts:
            found_id: str | None = self._get_alert_product_id(alert)
            if found_id:
                mapping[found_id] = alert

        return mapping

    def _get_alert_product_id(self, alert: Any) -> str | None:
        """Helper to extract SentinelOne ID from an alert object safely."""
        if self._is_valid_s1_id(alert.ticket_id):
            return str(alert.ticket_id)

        if alert.alert_group_identifier:
            context_value: str | None = self.soar_job.get_context_property(
                constants.ENTITY_TYPE,
                alert.alert_group_identifier,
                constants.ALERT_ID_CONTEXT_PROPERTY
            )
            if self._is_valid_s1_id(context_value):
                return str(context_value)

        return None

    def _map_alerts_to_metadata(
        self,
        job_case: JobCase,
        alerts: list[Alert],
        ids_map: SingleJson
    ) -> None:
        """Links SentinelOne objects and sets metadata manually."""
        for alert in alerts:
            s1_id_string: str = str(alert.alert_id)
            match: Any = ids_map.get(s1_id_string)
            if match:
                if not getattr(match, "incident", None):
                    match.incident = alert

                job_case.alert_metadata[match.identifier] = SyncMetadata(
                    status=str(alert.incident_status).lower(),
                    severity=None,
                    incident_id=s1_id_string,
                    closure_reason=alert.verdict,
                    closure_comment=""
                )

    def remove_synced_data_from_db(
        self,
        job_case: JobCase,
        product_details: list[Alert],
    ) -> None:
        """Removes synced entries from DB if both alerts are closed."""
        case_id: str = str(job_case.case_detail.id_)

        alert_lookup = {str(a.alert_id): a for a in product_details}

        for alert in job_case.case_detail.alerts:
            alert_s1_id: str | None = self._get_alert_product_id(alert)
            if not alert_s1_id:
                continue

            matching_s1_alert = alert_lookup.get(alert_s1_id)

            if not matching_s1_alert:
                continue

            if self.is_alert_and_product_closed(job_case, matching_s1_alert):
                entries = [(case_id, str(matching_s1_alert.alert_id))]
                self._remove_synced_entries(entries)

    def is_alert_and_product_closed(self, job_case: JobCase, s1_alert: Alert) -> bool:
        """Checks if both SecOps alert and SentinelOne Alert are closed."""
        product_id: str = str(s1_alert.alert_id)
        secops_alert: Any = job_case.product_ids_from_secops_alerts.get(product_id)
        if not secops_alert:
            return False

        is_alert_closed: bool = secops_alert.status == constants.ALERT_CLOSED_STATUS
        s1_status: str = str(s1_alert.incident_status).lower()
        is_product_closed: bool = s1_status == constants.SENTINELONE_RESOLVED.lower()

        return is_alert_closed and is_product_closed

    def sync_status(self, job_case: JobCase) -> None:
        """Orchestrates bi-directional status sync."""
        sync_result: Any = job_case.get_status_to_sync(constants.SENTINELONE_RESOLVED)
        self._sync_product_status_to_case(sync_result, job_case)
        self._sync_case_status_to_product(sync_result, job_case)

    def _sync_product_status_to_case(self, sync_result: Any, job_case: JobCase) -> None:
        """Syncs S1 -> SecOps status."""
        for alert, meta in sync_result.alerts_to_close_in_soar:
            reason, root_cause = self._map_s1_verdict_to_secops(meta.closure_reason)
            self.logger.info(
                f"Syncing closure for S1 Alert {meta.incident_id} with "
                f"verdict {meta.closure_reason}"
            )
            self.sync_product_status_to_case(
                case_id=job_case.case_detail.id_,
                alert_id=alert.identifier,
                reason=reason,
                root_cause=root_cause,
                comment=(
                    f"Closed via Sync. SentinelOne Alert "
                    f"{meta.incident_id} Resolved."
                )
            )
            self._remove_synced_entries([(job_case.case_detail.id_, meta.incident_id)])

    def _map_s1_verdict_to_secops(self, verdict: str) -> tuple[str, str]:
        """Maps SentinelOne verdict to SecOps reason."""
        if verdict == constants.SENTINELONE_TRUE_POSITIVE:
            return (
                constants.REASON_MALICIOUS,
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            )

        if verdict == constants.SENTINELONE_FALSE_POSITIVE:
            return (
                constants.REASON_NOT_MALICIOUS,
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            )

        return (
            constants.REASON_INCONCLUSIVE,
            CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
        )

    def _sync_case_status_to_product(self, sync_result: Any, job_case: JobCase) -> None:
        """Manages the flow if there are alerts to close."""
        requests = sync_result.incidents_to_close_in_product
        if not requests:
            return

        case_id = str(job_case.case_detail.id_)
        case_reason = self._get_case_closure_reason(job_case)
        verdict_groups, alert_ids = self._build_verdict_batches(requests, case_reason)

        if alert_ids:
            self._process_status_batches(case_id, verdict_groups, alert_ids)

    def _get_case_closure_reason(self, job_case: JobCase) -> str | None:
        """Gets case closure reason if applicable."""
        if job_case.case_detail.status != CaseDataStatus.CLOSED:
            return None

        try:
            details_list: list[SingleJson] = self.soar_job.get_case_closure_details(
                [job_case.case_detail.id_]
            )
            return details_list[0].get("reason", "") if details_list else None

        except Exception as error:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Failed to get case closure reason: {error}")
            return None

    def _build_verdict_batches(
        self,
        closure_requests: list[SingleJson],
        case_closure_reason: str | None,
    ) -> tuple[dict[str, list[str]], list[str]]:
        """Groups alerts by target verdict using defaultdict."""
        verdict_groups = defaultdict(list)
        alert_ids: list = []

        for req in closure_requests:
            alert_id = req["meta"].incident_id
            reason = self._determine_secops_closure_reason(req, case_closure_reason)
            verdict = self._map_secops_reason_to_s1_verdict(reason)
            verdict_groups[verdict].append(alert_id)
            alert_ids.append(alert_id)

        return verdict_groups, alert_ids

    def _determine_secops_closure_reason(
        self,
        closure_request: SingleJson,
        case_closure_reason: str | None,
    ) -> str:
        """Selects appropriate closure reason."""
        if closure_request.get("is_case_closed") and case_closure_reason:
            return case_closure_reason

        return closure_request.get("reason", "")

    def _map_secops_reason_to_s1_verdict(self, reason: str) -> str | None:
        """Maps SecOps reason to SentinelOne verdict."""
        if not reason:
            return None

        clean_reason: str = reason.strip()
        if clean_reason == constants.REASON_MALICIOUS:
            return constants.SENTINELONE_TRUE_POSITIVE

        if clean_reason == constants.REASON_NOT_MALICIOUS:
            return constants.SENTINELONE_FALSE_POSITIVE

        return None

    def _process_status_batches(
        self, case_id: str, verdict_groups: dict, alert_ids: list[str]
    ) -> None:
        """Handles the retry wrapper, logging, and database cleanup."""
        try:
            self._retry(self._execute_sentinelone_api_calls, verdict_groups, alert_ids)
            self._remove_synced_entries([(case_id, aid) for aid in alert_ids])
        except (RequestsConnectionError, SentinelOneV2ManagerError) as error:
            self.logger.error(f"Batch sync failed for Case {case_id}: {error}")

    def _execute_sentinelone_api_calls(
        self,
        verdict_groups: dict[str, list[str]],
        alert_ids: list[str],
    ) -> None:
        """Runs the SentinelOne API calls."""
        for verdict, ids in verdict_groups.items():
            if verdict and ids:
                self.manager.update_cloud_detection_alert_verdict(
                    alert_ids=ids, analyst_verdict=verdict
                )
                self.logger.info(f"Updated verdict '{verdict}' for IDs: {ids}")

        if not alert_ids:
            return

        self.manager.update_cloud_detection_alert_incident_status(
            alert_ids=alert_ids, status=constants.SENTINELONE_RESOLVED
        )
        self.logger.info(f"Resolved S1 Alerts IDs: {alert_ids}")

    def sync_comments(self, job_case: JobCase) -> None:
        """SentinelOne -> SecOps Comments Sync.

        Args:
            job_case (JobCase): The SecOps case to sync comments for.
        """

    def sync_severity(self, job_case: JobCase) -> None:
        """SentinelOne -> SecOps Priority Sync.

        Args:
            job_case (JobCase): The SecOps case to sync severity for.
        """

    def sync_assignee(self, job_case: JobCase) -> None:
        """SentinelOne -> SecOps Assignee Sync.

        Args:
            job_case (JobCase): The SecOps case to sync assignee for.
        """

    def sync_tags(self, job_case: JobCase) -> None:
        """SentinelOne -> SecOps Tags Sync.

        Args:
            job_case (JobCase): The SecOps case to sync tags for.
        """

    def _get_secops_closure_details(self, product_class: str) -> tuple[str, str]:
        return self._map_s1_verdict_to_secops(product_class)


def main() -> NoReturn:
    """Main entry point."""
    SyncAlertsV2().start()


if __name__ == "__main__":
    main()
