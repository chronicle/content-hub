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

import copy
import sys

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import unix_now

from TIPCommon.consts import TIMEOUT_THRESHOLD, UNIX_FORMAT
from TIPCommon.data_models import BaseAlert
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import (
    dict_to_flat,
)
from TIPCommon.utils import is_empty_string_or_none, is_test_run
from TIPCommon.base.connector import Connector

from sysdig_secure.core.SysdigSecureAuthManager import AuthManagerParams, AuthManager
from sysdig_secure.core.SysdigSecureConstants import (
    DEFAULT_LIMIT,
    EVENTS_CONNECTOR,
    MAX_LIMIT,
    SEVERITIES,
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_DEVICE_PRODUCT,
    SEVERITY_TO_SOAR_SEVERITY_MAPPING,
    INTEGRATION_PREFIX,
    STORED_IDS_LIMIT,
    TIME_DELTA_MS,
)
from sysdig_secure.core.SysdigSecureDatamodels import Event
from sysdig_secure.core.SysdigSecureManager import ApiManager
from sysdig_secure.core.SysdigSecureUtils import convert_milliseconds_to_nanoseconds


class EventsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None
        self.end_timestamp = None

    def extract_params(self) -> None:
        """Extract connector parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = AuthManagerParams(
            api_root=self.params.api_root,
            api_token=self.params.api_token,
            verify_ssl=self.params.verify_ssl,
        )

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_events_to_fetch = self.param_validator.validate_positive(
            param_name="Max Events To Fetch", value=self.params.max_events_to_fetch
        )
        self.params.max_events_to_fetch = self.param_validator.validate_upper_limit(
            param_name="Max Events To Fetch",
            value=self.params.max_events_to_fetch,
            limit=MAX_LIMIT,
            default_value=DEFAULT_LIMIT,
        )
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=SEVERITIES,
            )

    def init_managers(self) -> None:
        """Create manager instance objects"""
        auth_manager = AuthManager(params=self.params.auth_params)
        session = auth_manager.prepare_session()

        self.manager = ApiManager(
            api_root=self.params.api_root,
            session=session,
            logger=self.logger
        )

    def get_last_success_time(self, *_) -> int:
        """Get last_success_time for connector from DB (or FileStorage)."""
        last_success_timestamp = super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=UNIX_FORMAT,
        )
        self.end_timestamp = last_success_timestamp + TIME_DELTA_MS
        return last_success_timestamp

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: Event) -> None:
        """Store alert id in connector IDs cache

        Args:
            alert (Event): Event dataclass

        """
        self.context.existing_ids.append(alert.alert_id)

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if alert is overflowed

        Args:
            alert_info (AlertInfo): AlertInfo object

        Returns:
            True if alert is overflowed, False otherwise
        """
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def set_last_success_time(self, all_alerts: list[Event], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        Args:
            all_alerts ([Event]): list of all fetched Alert dataclasses

        """
        if all_alerts:
            super().set_last_success_time(alerts=all_alerts, timestamp_key="timestamp")
        else:
            now_timestamp = unix_now()
            timestamp = (
                self.end_timestamp
                if self.end_timestamp < now_timestamp else now_timestamp
            )
            self.siemplify.save_timestamp(new_timestamp=timestamp)

    def write_context_data(self, all_alerts: list[Event]) -> None:
        """Save connector context data into DB (or FileStorage)

        Args:
            all_alerts ([Event]): list of all fetched Event dataclasses

        """
        if all_alerts:
            self.logger.info("Saving existing ids.")

            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=STORED_IDS_LIMIT,
            )

    def get_alerts(self) -> list[Event]:
        """Fetch new alerts

        Returns:
            list[Event]: List of Event dataclasses
        """
        fetched_alerts = self.manager.get_events(
            start_timestamp=convert_milliseconds_to_nanoseconds(
                self.context.last_success_timestamp
            ),
            end_timestamp=convert_milliseconds_to_nanoseconds(self.end_timestamp),
            limit=self.params.max_events_to_fetch,
            exclude_rule_names=self.params.use_dynamic_list_as_a_blocklist,
            siemplify=self.siemplify,
            lowest_severity=self.params.lowest_severity_to_fetch,
            custom_filter_query=self.params.custom_filter_query,
            existing_ids=self.context.existing_ids,
            rule_names=self.siemplify.whitelist,
        )

        self.logger.info(f"Number of fetched alerts: {len(fetched_alerts)}")
        return fetched_alerts

    def build_events_data(self, alert: Event) -> list[dict[str, str]]:
        """Build events data out of alert

        Args:
            alert (Event): Event dataclass

        Returns:
            list[dict[str, str]]: list of flattened event dicts
        """
        events = [self.build_main_event(alert)]
        return events

    @staticmethod
    def build_main_event(alert: Event) -> dict[str, str]:
        """Build main event data out of alert

        Args:
            alert (Event): Event dataclass

        Returns:
            dict[str, str]: main event flat dict
        """
        alert_data = copy.deepcopy(alert.raw_data)
        return dict_to_flat(alert_data)

    def create_alert_info(self, alert: Event) -> AlertInfo:
        """Create AlertInfo object out of an alert

        Args:
            alert (Event): Event dataclass

        Returns:
            AlertInfo: AlertInfo object
        """
        alert_info = AlertInfo()

        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = f"{INTEGRATION_PREFIX}{alert.alert_id}"
        alert_info.name = alert.rule_name
        alert_info.description = alert.output
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = SEVERITY_TO_SOAR_SEVERITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = alert.rule_name
        alert_info.source_grouping_identifier = alert.rule_name
        alert_info.start_time = alert.timestamp
        alert_info.end_time = alert.timestamp
        alert_info.environment = self.env_common.get_environment(alert.raw_flat_data)
        alert_info.events = self.build_events_data(alert=alert)

        return alert_info

    def process_alerts(
        self,
        filtered_alerts: list[BaseAlert],
        timeout_threshold: float = TIMEOUT_THRESHOLD,
    ) -> tuple[list[AlertInfo], list[BaseAlert]]:
        """Main alert processing loop

        Args:
            filtered_alerts ([BaseAlert]): list of filtered BaseAlert objects
            timeout_threshold (float): timeout threshold for connector execution

        Returns:
            tuple containing list of AlertInfo objects, and list of BaseAlert objects
        """
        processed_alerts, all_alerts = super().process_alerts(
            filtered_alerts, timeout_threshold
        )

        return processed_alerts, all_alerts


def main() -> None:
    """main"""
    script_name = EVENTS_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = EventsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
