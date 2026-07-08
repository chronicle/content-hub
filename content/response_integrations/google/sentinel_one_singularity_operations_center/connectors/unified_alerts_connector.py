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
from typing import TYPE_CHECKING

import dateutil.parser
from SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.base.connector import Connector
from TIPCommon.consts import IDS_DB_KEY, IDS_FILE_NAME
from TIPCommon.exceptions import ConnectorSetupError
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_content, write_ids_with_timestamp
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.transformation import dict_to_flat
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
from ..core.constants import SEVERITY_MAP
from ..core.data_models import SentinelOneAlert
from ..core.exceptions import SentinelOneSingularityOperationsCenterError

if TYPE_CHECKING:
    import requests
    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

CONNECTOR_SCRIPT_NAME = (
    "SentinelOne Singularity Operations Center - Unified Alerts Connector"
)
MAX_CACHE_SIZE = 1100
PRUNED_CACHE_SIZE = 1000


class UnifiedAlertsConnector(Connector):
    """SentinelOne Singularity Operations Center Connector."""

    def __init__(self, is_test_connector_run: bool) -> None:  # noqa: FBT001
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
        self._originally_cached_ids = set(self.context.existing_ids.keys())

    def _prune_cache(self) -> None:
        """Prune oldest cache entries down to PRUNED_CACHE_SIZE based on insertion order."""
        self.logger.info(
            f"Cache size ({len(self.context.existing_ids)}) exceeded limit ({MAX_CACHE_SIZE}). "
            f"Pruning oldest entries down to {PRUNED_CACHE_SIZE}."
        )
        excess = len(self.context.existing_ids) - PRUNED_CACHE_SIZE
        if excess > 0:
            for key in list(self.context.existing_ids.keys())[:excess]:
                del self.context.existing_ids[key]

    def store_alert_in_cache(self, processed_alert: SentinelOneAlert) -> None:
        """Store processed alert ID and its updated timestamp in cache."""
        self.context.existing_ids[processed_alert.alert_id] = (
            convert_datetime_to_unix_time(
                dateutil.parser.parse(processed_alert.updated_at)
            )
        )
        if len(self.context.existing_ids) > MAX_CACHE_SIZE:
            self._prune_cache()

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
        """Save the updated success timestamp based on createdAt to prevent horizon leaps."""
        super().set_last_success_time(
            alerts=alerts,
            timestamp_key="created_at",
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

        Args:
            alert_info (AlertInfo): The alert info to evaluate.

        Returns:
            bool: True if overflowed, False otherwise.
        """
        return not self.params.disable_overflow and is_overflowed(
            self.siemplify,
            alert_info,
            self.is_test_run,
        )

    def _is_unprocessed(self, alert: SentinelOneAlert) -> bool:
        """Check if an alert is new or has been updated since last fetch.

        Args:
            alert (SentinelOneAlert): The alert to check.

        Returns:
            bool: True if alert is new or updated, False otherwise.
        """
        return convert_datetime_to_unix_time(
            dateutil.parser.parse(alert.updated_at)
        ) > self.context.existing_ids.get(alert.alert_id, -1)

    def get_alerts(self) -> list[SentinelOneAlert]:
        """Fetch alerts from SentinelOne.

        Returns:
            list[SentinelOneAlert]: The list of fetched alerts.
        """
        start_timestamp_ms = convert_datetime_to_unix_time(
            self.context.last_success_timestamp
        )

        self.logger.info(
            f"Fetching up to {self.params.max_alerts_to_fetch} unified alerts. "
            f"Last run success time: {start_timestamp_ms} ms. Start timestamp: {start_timestamp_ms} ms."
        )

        alerts_generator = self.manager.yield_unified_alerts(
            start_timestamp_ms=start_timestamp_ms,
            lowest_severity=self.params.lowest_severity_to_fetch,
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
        return pass_whitelist_filter(
            siemplify=self.siemplify,
            whitelist_as_a_blacklist=self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="classification",
            whitelist=self.params.whitelist,
        )

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
