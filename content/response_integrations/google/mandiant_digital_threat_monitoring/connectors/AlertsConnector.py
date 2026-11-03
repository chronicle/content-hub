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
import datetime
import sys
import uuid

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.consts import DATETIME_FORMAT, TIMEOUT_THRESHOLD
from TIPCommon.data_models import BaseAlert
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.transformation import (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
    dict_to_flat,
)
from TIPCommon.utils import is_empty_string_or_none, is_test_run
from TIPCommon.base.connector import Connector
from ..core import constants
from ..core.datamodels import Alert
from ..core import AuthenticationManager as auth_manager
from ..core.MandiantDTMManager import ApiManager, ApiParameters
from ..core.constants import EVENTS_LIMIT


class AlertsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None

    def extract_params(self) -> None:
        """Extract action parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = auth_manager.SessionAuthenticationParameters(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            gti_api_key=self.params.gtiapi_key,
            verify_ssl=self.params.verify_ssl,
        )
        self.params.api_params = ApiParameters(api_root=self.params.api_root)

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch", value=self.params.max_alerts_to_fetch
        )
        self.params.max_alerts_to_fetch = self.param_validator.validate_upper_limit(
            param_name="Max Alerts To Fetch",
            value=self.params.max_alerts_to_fetch,
            limit=constants.MAX_LIMIT,
            default_value=constants.MAX_LIMIT,
        )
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        if not is_empty_string_or_none(self.params.lowest_severity_to_fetch):
            self.params.lowest_severity_to_fetch = self.param_validator.validate_ddl(
                param_name="Lowest Severity To Fetch",
                value=self.params.lowest_severity_to_fetch,
                ddl_values=constants.SEVERITIES,
            )

    def init_managers(self) -> None:
        """Create manager instance objects"""
        session = auth_manager.get_authenticated_session(
            auth_params=self.params.auth_params
        )

        self.manager = ApiManager(
            session=session,
            api_params=self.params.api_params,
            logger=self.logger,
            gti_api_key=self.params.auth_params.gti_api_key,
        )

    def get_last_success_time(self, *_) -> datetime.datetime:
        """Get last_success_time for connector from DB (or FileStorage)."""
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            metric="hours",
            time_format=DATETIME_FORMAT,
            date_time_format="%Y-%m-%dT%H:%M:%SZ",
        )

    def read_context_data(self) -> None:
        """Read connector's context data from DB (or FileStorage)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = list(read_ids(self.siemplify))

    def store_alert_in_cache(self, alert: Alert) -> None:
        """Store alert id in connector IDs cache

        Args:
            alert (Alert): Alert dataclass

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

    def set_last_success_time(self, all_alerts: list[Alert], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses

        """
        super().set_last_success_time(alerts=all_alerts, timestamp_key="created_at")

    def write_context_data(self, all_alerts: list[Alert]) -> None:
        """Save connector context data into DB (or FileStorage)

        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses

        """
        if all_alerts:
            self.logger.info("Saving existing ids.")

            write_ids(
                self.siemplify,
                self.context.existing_ids,
                stored_ids_limit=constants.STORED_IDS_LIMIT,
            )

    def get_alerts(self) -> list[Alert]:
        """Fetch new alerts

        Returns:
            List of Alert dataclasses
        """
        fetched_alerts = self.manager.get_alerts(
            timestamp=self.context.last_success_timestamp,
            lowest_severity=self.params.lowest_severity_to_fetch,
            monitor_ids=convert_comma_separated_to_list(self.params.monitor_id_filter),
            limit=self.params.max_alerts_to_fetch,
            existing_ids=set(self.context.existing_ids),
            alert_types=(
                self.siemplify.whitelist
                if not self.params.use_dynamic_list_as_a_blocklist
                else None
            ),
            siemplify=self.siemplify,
        )

        self.logger.info(f"Number of fetched alerts: {len(fetched_alerts)}")
        return fetched_alerts

    def filter_alerts(self, alerts: list[Alert]) -> list[Alert]:
        """Filter fetched alerts to exclude already fetched ones

        Args:
            alerts ([Alert]): list of Alert dataclasses

        Returns:
            [Alert]: list of filtered Alert dataclasses sorted by alert.created_at
        """
        return sorted(
            filter_old_alerts(
                self.siemplify,
                alerts=alerts,
                existing_ids=set(self.context.existing_ids),
                id_key="alert_id",
            ),
            key=lambda _alert: _alert.created_at,
        )

    def pass_filters(self, alert: Alert) -> bool:
        """Check if alert passes dynamic list filter

        Args:
            alert (Alert): Alert dataclass

        Returns:
            bool: True if passes filter, False otherwise
        """
        if self.siemplify.whitelist and not pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            model=alert,
            model_key="alert_type",
        ):
            return False

        return True

    def build_events_data(self, alert: Alert) -> list[dict]:
        """Build events data out of alert

        Args:
            alert (Alert): Alert dataclass

        Returns:
            [dict]: list of flattened event dicts
        """
        events = [self.build_main_event(alert)]
        events.extend(self.build_topic_events(alert))
        return events

    @staticmethod
    def build_main_event(alert: Alert) -> dict:
        """Build main event data out of alert

        Args:
            alert (Alert): Alert dataclass

        Returns:
            dict: main event flat dict
        """
        alert_data = copy.deepcopy(alert.raw_data)

        alert_data.get("doc", {}).pop("body", None)
        alert_data.pop("topics", [])
        alert_data["event_type"] = constants.MAIN_ALERT_EVENT_TYPE
        alert_data["labels"] = convert_list_to_comma_string(
            [label.get("label") for label in alert_data.get("labels", [])]
        )

        return dict_to_flat(alert_data)

    @staticmethod
    def build_topic_events(alert: Alert) -> list[dict]:
        """Build events data out of alert topics

        Args:
            alert (Alert): Alert dataclass

        Returns:
            [dict]: list of topic events flat dicts
        """
        topics_data = copy.deepcopy([topic.raw_data for topic in alert.topics])
        topic_events = []

        for topic in topics_data:
            topic["event_type"] = topic.get("type")
            topic["timestamp"] = alert.raw_data.get("created_at")
            topic[topic.get("type")] = topic.get("value")

            topic_events.append(dict_to_flat(topic))

        return topic_events

    def create_alert_info(self, alert: Alert) -> AlertInfo:
        """Create AlertInfo object out of and alert

        Args:
            alert (Alert): Alert dataclass

        Returns:
            AlertInfo: AlertInfo object
        """
        alert_info = AlertInfo()

        alert_info.ticket_id = alert.alert_id
        alert_info.display_id = f"{constants.INTEGRATION_PREFIX}{alert.alert_id}"
        alert_info.name = alert.title
        alert_info.description = alert.alert_summary
        alert_info.device_vendor = constants.DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or constants.DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = constants.SEVERITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = f"{constants.PROVIDER_NAME}: {alert.alert_type}"
        alert_info.source_grouping_identifier = (
            alert.aggregated_under_id or alert.monitor_name
        )
        alert_info.start_time = alert.created_at
        alert_info.end_time = alert.created_at
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

        processed_alerts = self.split_processed_alerts(processed_alerts)

        return processed_alerts, all_alerts

    @staticmethod
    def split_processed_alerts(processed_alerts: [AlertInfo]):
        """Split processed alerts to contain EVENTS_LIMIT amount events per each alert

        Args:
            processed_alerts ([AlertInfo]): list of AlertInfo objects

        Returns:
            ([AlertInfo]): list of split AlertInfo objects
        """
        split_alerts = []

        for processed_alert in processed_alerts:
            if len(processed_alert.events) > EVENTS_LIMIT:
                main_event = copy.deepcopy(processed_alert.events[0])

                for split_events in [
                    processed_alert.events[i : i + EVENTS_LIMIT - 1]
                    for i in range(1, len(processed_alert.events), EVENTS_LIMIT - 1)
                ]:
                    new_alert = copy.deepcopy(processed_alert)
                    new_alert.events = [main_event] + split_events
                    new_alert.display_id = f"{new_alert.display_id}_{str(uuid.uuid4())}"
                    split_alerts.append(new_alert)
            else:
                processed_alert.display_id = (
                    f"{processed_alert.display_id}_{str(uuid.uuid4())}"
                )
                split_alerts.append(processed_alert)

        return split_alerts


def main() -> None:
    """main"""
    script_name = constants.ALERTS_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = AlertsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
