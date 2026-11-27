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

import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import dateutil.parser
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, unix_now
from TIPCommon.base.connector import Connector
from TIPCommon.consts import (
    IDS_DB_KEY,
    IDS_FILE_NAME,
    NUM_OF_MILLI_IN_MINUTE,
    NUM_OF_MIN_IN_HOUR,
)
from TIPCommon.exceptions import ConnectorSetupError
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_content, write_ids_with_timestamp
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.transformation import dict_to_flat, string_to_multi_value
from TIPCommon.utils import is_overflowed, is_test_run

from ..core.api.api_client import (
    ApiParameters,
    SentinelOneSingularityOperationsCenterApiClient,
)
from ..core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
)
from ..core.constants import SEVERITY_MAP, STATUS_FILTER_MAP
from ..core.data_models import SentinelOneAlert
from ..core.exceptions import SentinelOneSingularityOperationsCenterError

if TYPE_CHECKING:
    from datetime import datetime

    import requests
    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

CONNECTOR_SCRIPT_NAME = (
    "SentinelOne Singularity Operations Center - Unified Alerts Connector"
)
MAX_CACHE_SIZE = 1100
PRUNED_CACHE_SIZE = 1000
MAX_PADDING_PERIOD_MINUTES = 1440
NUM_OF_MILLI_IN_HOUR = NUM_OF_MILLI_IN_MINUTE * NUM_OF_MIN_IN_HOUR


def _parse_status_filter(raw_value: str | None) -> list[str]:
    """Parse the comma-separated Status Filter into SentinelOne status enums.

    Args:
        raw_value: The raw parameter value.

    Returns:
        Unique SentinelOne status enums. Empty list means all statuses.

    Raises:
        ConnectorSetupError: If an unsupported status is provided.
    """
    statuses: list[str] = []
    for item in string_to_multi_value(raw_value or "", only_unique=True):
        key = item.upper()
        if key not in STATUS_FILTER_MAP:
            msg = (
                "Error executing connector: 'Unified Alerts Connector'. Reason: invalid "
                f"value '{item}' provided in 'Status Filter'. "
                "Supported values: New, In Progress, Resolved."
            )
            raise ConnectorSetupError(msg)
        status = STATUS_FILTER_MAP[key]
        if status not in statuses:
            statuses.append(status)
    return statuses


def _to_unix_ms(timestamp: str | None, fallback: datetime) -> int:
    """Convert an ISO timestamp to unix milliseconds, using fallback when it is empty.

    Args:
        timestamp: The ISO timestamp string.
        fallback: The datetime to use when timestamp is None or empty.

    Returns:
        The timestamp in unix milliseconds.
    """
    parsed = dateutil.parser.parse(timestamp) if timestamp else fallback
    return convert_datetime_to_unix_time(parsed)


class UnifiedAlertsConnector(Connector):
    """SentinelOne Singularity Operations Center Connector.

    Fetches unified alerts from SentinelOne using GraphQL. Checkpointing is based on
    the `lastSeenAt` timestamp to ensure accurate tracking across alert updates and creations,
    with processed alert IDs and timestamps cached to prevent duplicate ingestion.
    """

    def __init__(self, is_test_connector_run: bool) -> None:
        super().__init__(CONNECTOR_SCRIPT_NAME, is_test_connector_run)
        self.manager: SentinelOneSingularityOperationsCenterApiClient | None = None

    def validate_params(self) -> None:
        """Validate connector parameters.

        Raises:
            ConnectorSetupError: If parameter validation fails.
        """
        # Normalize boolean parameters
        self.params.use_dynamic_list_as_a_blocklist = (
            str(self.params.use_dynamic_list_as_a_blocklist).lower() == "true"
        )
        self.params.disable_overflow = (
            str(self.params.disable_overflow).lower() == "true"
        )

        # Validate Lowest Severity To Fetch
        if self.params.lowest_severity_to_fetch:
            val = self.params.lowest_severity_to_fetch.strip().upper()
            if val not in SEVERITY_MAP:
                msg = (
                    "Error executing connector: 'Alerts Connector'. "
                    f"Reason: invalid value provided. Supported values: {', '.join(SEVERITY_MAP.keys())}."
                )
                raise ConnectorSetupError(msg)

        # Validate Max Hours Backwards
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_backwards,
            print_value=True,
        )

        # Validate Max Alerts To Fetch
        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
            print_value=True,
        )

        padding = getattr(self.params, "padding_period", None)
        self.params.padding_period = (
            self.param_validator.validate_range(
                param_name="Padding Period",
                value=padding,
                min_limit=0,
                max_limit=MAX_PADDING_PERIOD_MINUTES,
                print_value=True,
            )
            if padding not in (None, "")
            else 0
        )

        self.params.status_filter = _parse_status_filter(
            getattr(self.params, "status_filter", None)
        )

    def init_managers(self) -> None:
        """Initialize API client."""
        auth_params = build_auth_params(self.siemplify)
        authenticator = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_root=auth_params.api_root,
            api_token=auth_params.api_token,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params = ApiParameters(
            api_root=auth_params.api_root,
        )

        self.manager = SentinelOneSingularityOperationsCenterApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    def read_context_data(self) -> None:
        """Read already processed alert IDs and timestamps."""
        self.logger.info("Reading already existing alert ids...")
        raw_ids = read_content(
            self.siemplify, IDS_FILE_NAME, IDS_DB_KEY, default_value_to_return={}
        )

        self.logger.info(f"Loaded raw context: {raw_ids}")
        self.context.existing_ids = raw_ids or {}

        # Capture a copy of the cached IDs at start. Since the base connector's loop calls
        # store_alert_in_cache(alert) (which adds the alert to the cache) BEFORE calling
        # create_alert_info(alert), checking self.context.existing_ids during create_alert_info
        # would always return True. This snapshot lets us detect if an alert was an update.
        # Negative timestamps mark alerts that were filtered out or overflowed (never
        # ingested into SOAR), so they are not treated as updates.
        self._originally_cached_ids = {
            alert_id
            for alert_id, last_seen_ms in self.context.existing_ids.items()
            if last_seen_ms > 0
        }

    def _prune_cache(self) -> None:
        """Prune least recently seen cache entries down to PRUNED_CACHE_SIZE."""
        self.logger.info(
            f"Cache size ({len(self.context.existing_ids)}) exceeded limit ({MAX_CACHE_SIZE}). "
            f"Pruning oldest entries down to {PRUNED_CACHE_SIZE}."
        )
        excess = len(self.context.existing_ids) - PRUNED_CACHE_SIZE
        if excess > 0:
            for key in list(self.context.existing_ids.keys())[:excess]:
                del self.context.existing_ids[key]

    def store_alert_in_cache(self, processed_alert: SentinelOneAlert) -> None:
        """Store processed alert ID and its lastSeenAt timestamp in cache.

        The list-query `lastSeenAt` is stored (same value `_is_unprocessed` compares
        against), and the key is re-inserted so pruning removes the least recently
        seen alerts instead of the first ever inserted ones.
        """
        self.context.existing_ids.pop(processed_alert.alert_id, None)
        self.context.existing_ids[processed_alert.alert_id] = (
            self._get_list_last_seen_ms(processed_alert)
        )
        if len(self.context.existing_ids) > MAX_CACHE_SIZE:
            self._prune_cache()

    def _mark_alert_as_not_ingested(self, alert_id: str) -> None:
        """Store the cached timestamp as negative for an alert that was not ingested.

        Args:
            alert_id: The ID of the filtered-out or overflowed alert.
        """
        if alert_id in self.context.existing_ids:
            self.context.existing_ids[alert_id] = -abs(
                self.context.existing_ids[alert_id]
            )

    def _get_list_last_seen_ms(self, alert: SentinelOneAlert) -> int:
        """Get the list-query lastSeenAt of an alert in unix milliseconds.

        Args:
            alert: The SentinelOne alert.

        Returns:
            The lastSeenAt in unix milliseconds, or the last success time if missing.
        """
        last_seen_at = (alert.raw_data or {}).get("lastSeenAt") or alert.last_seen_at
        return _to_unix_ms(last_seen_at, self.context.last_success_timestamp)

    def write_context_data(self, alerts: list[SentinelOneAlert]) -> None:
        """Write processed IDs to cache."""
        if not alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids_with_timestamp(self.siemplify, self.context.existing_ids)

    def get_last_success_time(self) -> int:
        """Calculate the start time for fetching alerts.

        Returns:
            int: The start timestamp in milliseconds.
        """
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
        )

    def set_last_success_time(self, alerts: list[SentinelOneAlert]) -> None:
        """Save the updated success timestamp based on lastSeenAt.

        Only alerts last seen at or after the previous last success time are used, so
        late alerts found in the padding window never move the checkpoint backwards.
        """
        last_success_ms = convert_datetime_to_unix_time(
            self.context.last_success_timestamp
        )
        newer_alerts = [
            alert
            for alert in alerts
            if alert.last_seen_at
            and _to_unix_ms(alert.last_seen_at, self.context.last_success_timestamp)
            >= last_success_ms
        ]
        super().set_last_success_time(
            alerts=newer_alerts,
            timestamp_key="last_seen_at",
            convert_a_string_timestamp_to_unix=True,
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        """Check if max alerts count has been reached.

        Args:
            processed_alerts (list[AlertInfo]): The list of processed alerts.

        Returns:
            bool: True if max alerts processed, False otherwise.
        """
        return len(processed_alerts) >= self.params.max_alerts_to_fetch

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if alert is overflowed.

        Updates of already ingested alerts are never counted towards overflow,
        otherwise repeated updates of the same alert create overflow cases.

        Args:
            alert_info (AlertInfo): The alert info to evaluate.

        Returns:
            bool: True if overflowed, False otherwise.
        """
        if alert_info.ticket_id in self._originally_cached_ids:
            self.logger.info(
                f"Alert {alert_info.ticket_id} is an update. Skipping overflow check."
            )
            return False

        overflowed = not self.params.disable_overflow and is_overflowed(
            self.siemplify,
            alert_info,
            self.is_test_run,
        )
        if overflowed:
            self._mark_alert_as_not_ingested(alert_info.ticket_id)
        return overflowed

    def _is_unprocessed(self, alert: SentinelOneAlert) -> bool:
        """Check if an alert is new or has been updated/reseen since last fetch.

        Args:
            alert (SentinelOneAlert): The alert to check.

        Returns:
            bool: True if alert is new or updated/reseen, False otherwise.
        """
        cached_ms = self.context.existing_ids.get(alert.alert_id)
        if cached_ms is None:
            return True
        return self._get_list_last_seen_ms(alert) > abs(cached_ms)

    def _calculate_fetch_start_ms(self, last_success_ms: int) -> int:
        """Look back Padding Period minutes from the last success time.

        The start is bounded by Max Hours Backwards and is never later than the
        last success time.

        Args:
            last_success_ms: The last success time in unix milliseconds.

        Returns:
            The fetch start timestamp in unix milliseconds.
        """
        if not self.params.padding_period:
            return last_success_ms

        padded_start_ms = (
            last_success_ms - self.params.padding_period * NUM_OF_MILLI_IN_MINUTE
        )
        earliest_allowed_ms = (
            unix_now() - self.params.max_hours_backwards * NUM_OF_MILLI_IN_HOUR
        )
        return min(last_success_ms, max(padded_start_ms, earliest_allowed_ms))

    def get_alerts(self) -> list[SentinelOneAlert]:
        """Fetch alerts from SentinelOne.

        Returns:
            list[SentinelOneAlert]: The list of fetched alerts.
        """
        last_success_ms = convert_datetime_to_unix_time(
            self.context.last_success_timestamp
        )
        start_timestamp_ms = self._calculate_fetch_start_ms(last_success_ms)

        self.logger.info(
            f"Fetching up to {self.params.max_alerts_to_fetch} unified alerts. "
            f"Last run success time: {last_success_ms} ms. "
            f"Padding period: {self.params.padding_period} min. "
            f"Start timestamp: {start_timestamp_ms} ms. "
            f"Status filter: {self.params.status_filter or 'ALL'}."
        )

        alerts_generator = self.manager.yield_unified_alerts(
            start_timestamp_ms=start_timestamp_ms,
            lowest_severity=self.params.lowest_severity_to_fetch,
            statuses=self.params.status_filter,
        )

        enriched_alerts: list[SentinelOneAlert] = []
        for raw_alert in alerts_generator:
            # Check if timeout is approaching before processing next alert
            if is_approaching_timeout(
                connector_starting_time=self.connector_start_time,
                python_process_timeout=self.params.python_process_timeout,
            ):
                self.logger.info("Timeout is approaching. Stopping alert ingestion.")
                break

            alert = SentinelOneAlert(raw_alert)
            if not self._is_unprocessed(alert):
                continue

            try:
                alert.details = self.manager.get_alert_details(alert.alert_id)
                enriched_alerts.append(alert)
            except SentinelOneSingularityOperationsCenterError as e:
                self.logger.info(
                    f"Failed to fetch details for alert {alert.alert_id}. Skipping. Error: {e}"
                )
                continue

            if len(enriched_alerts) >= self.params.max_alerts_to_fetch:
                break

        return enriched_alerts

    def pass_filters(self, alert: SentinelOneAlert) -> bool:
        """Check if the alert passes the whitelist/blocklist filter on classification.

        Args:
            alert (SentinelOneAlert): The alert to evaluate.

        Returns:
            bool: True if the alert passes, False otherwise.
        """
        classification = alert.classification.upper() if alert.classification else ""
        whitelist = (
            [item.upper() for item in self.params.whitelist]
            if self.params.whitelist
            else None
        )

        if not pass_whitelist_filter(
            siemplify=self.siemplify,
            whitelist_as_a_blacklist=self.params.use_dynamic_list_as_a_blocklist,
            model=SimpleNamespace(classification=classification),
            model_key="classification",
            whitelist=whitelist,
        ):
            # Cache filtered-out alerts (as not ingested) so the padding window
            # doesn't re-fetch them.
            self.store_alert_in_cache(alert)
            self._mark_alert_as_not_ingested(alert.alert_id)
            return False

        return True

    def create_alert_info(self, processed_alert: SentinelOneAlert) -> AlertInfo:
        """Map raw SentinelOne alert to Siemplify AlertInfo object.

        Args:
            processed_alert (SentinelOneAlert): The processed alert.

        Returns:
            AlertInfo: The mapped AlertInfo object.
        """
        flat_alert = dict_to_flat(
            processed_alert.details.raw_data if processed_alert.details else {}
        )
        environment = self.env_common.get_environment(flat_alert)

        return processed_alert.as_alert_info(
            environment=environment,
            is_update=processed_alert.alert_id in self._originally_cached_ids,
            last_success_timestamp=self.context.last_success_timestamp,
            device_product_field=getattr(self.params, "device_product_field", None),
        )


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = UnifiedAlertsConnector(is_test)
    connector.start()
