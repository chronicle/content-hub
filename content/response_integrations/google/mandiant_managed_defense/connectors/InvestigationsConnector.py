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
import json

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import unix_now, convert_datetime_to_unix_time
from TIPCommon.transformation import dict_to_flat, convert_list_to_comma_string
from TIPCommon.consts import DATETIME_FORMAT
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_test_run
from TIPCommon.base.connector import Connector
from ..core import constants
from ..core.datamodels import Alert
from ..core import exceptions
from ..core import AuthenticationManager as auth_manager
from ..core.MandiantMDManager import ApiManager, ApiParameters


class InvestigationsConnector(Connector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager: ApiManager | None = None
        self.end_timestamp: str | None = None
        self.end_timestamp_dt: datetime.datetime | None = None
        self.status_filter_string: str | None = None

    def extract_params(self) -> None:
        """Extract connector parameters and populate them into .params container."""
        super().extract_params()

        self.params.auth_params = auth_manager.SessionAuthenticationParameters(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            verify_ssl=self.params.verify_ssl,
        )
        self.params.api_params = ApiParameters(api_root=self.params.api_root)

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self.params.max_investigations_to_fetch = (
            self.param_validator.validate_positive(
                param_name="Max Investigations To Fetch",
                value=self.params.max_investigations_to_fetch,
            )
        )
        self.params.max_investigations_to_fetch = (
            self.param_validator.validate_upper_limit(
                param_name="Max Investigations To Fetch",
                value=self.params.max_investigations_to_fetch,
                limit=constants.MAX_LIMIT,
                default_value=constants.MAX_LIMIT,
            )
        )
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )
        self.params.padding_time = self.param_validator.validate_range(
            param_name="Padding Time",
            value=self.params.padding_time,
            min_limit=constants.MIN_PADDING_LIMIT,
            max_limit=constants.MAX_PADDING_LIMIT,
        ) if self.params.padding_time else 0
        self.params.status_filter = self.param_validator.validate_csv(
            param_name="Status Filter",
            csv_string=(self.params.status_filter or "").lower(),
            possible_values=constants.ALERT_STATUSES,
        )
        self.status_filter_string = convert_list_to_comma_string(
            self.params.status_filter
        )

    def init_managers(self) -> None:
        """Create manager instance objects"""
        session = auth_manager.get_authenticated_session(
            auth_params=self.params.auth_params
        )

        self.manager = ApiManager(
            session=session,
            api_params=self.params.api_params,
            chronicle_soar=self.siemplify,
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
        if alert.alert_id not in self.context.existing_ids:
            self.context.existing_ids.append(alert.alert_id)

    def set_last_success_time(self, all_alerts: list[Alert], *_) -> None:
        """Save last_success_time into DB (or FileStorage)

        Args:
            all_alerts ([Alert]): list of all fetched Alert dataclasses

        """
        if not all_alerts:
            last_timestamp = min(
                unix_now(), convert_datetime_to_unix_time(self.end_timestamp_dt)
            )
            self.logger.info(f"Last timestamp is: {last_timestamp}")
            self.siemplify.save_timestamp(new_timestamp=last_timestamp)
        else:
            super().set_last_success_time(alerts=all_alerts, timestamp_key="modified")

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
        last_success_dt = datetime.datetime.strptime(
            self.context.last_success_timestamp, constants.TIME_FORMAT
        )
        self.end_timestamp_dt = last_success_dt + datetime.timedelta(
            hours=constants.FETCH_INTERVAL)
        self.end_timestamp = datetime.datetime.strftime(
            self.end_timestamp_dt, constants.TIME_FORMAT
        )
        start_timestamp = datetime.datetime.strftime(
            last_success_dt - datetime.timedelta(hours=self.params.padding_time),
            constants.TIME_FORMAT
            )

        fetched_alerts = self.manager.get_investigations(
            timestamp=start_timestamp,
            end_timestamp=self.end_timestamp,
            limit=self.params.max_investigations_to_fetch,
            existing_ids=self.context.existing_ids,
        )

        self.logger.info(f"Total alerts to process: {len(fetched_alerts)}")

        return fetched_alerts

    def process_alert(self, alert: Alert) -> Alert:
        """Processing alert for events enrichment

        Args:
            alert: The alert to process.

        Returns:
            The processed alert.
        """
        self.logger.info("Fetching alert events")
        alert.events = self.manager.get_investigation_details(alert.external_id)
        return alert

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
            key=lambda _alert: _alert.modified,
        )

    def pass_filters(self, alert: Alert) -> bool:
        """Check if alert passes dynamic list filter

        Args:
            alert (Alert): Alert dataclass

        Returns:
            bool: True if passes filter, False otherwise
        """
        if (
            self.siemplify.whitelist
            and not pass_whitelist_filter(
                self.siemplify,
                self.params.use_dynamic_list_as_a_blocklist,
                model=alert,
                model_key="name",
            )
        ) or not self.pass_status_filter(alert):
            return False

        return True

    def pass_status_filter(self, alert: Alert) -> bool:
        """Check if alert passes status filter
        Args:
            alert (Alert): Alert dataclass
        Returns:
            bool: True if passes filter, False otherwise
        """
        if self.params.status_filter:
            if alert.status not in self.params.status_filter:
                self.logger.info(
                    f"Alert {alert.alert_id} with status "
                    f"{alert.status} did not pass the filter. "
                    f"Acceptable statuses are: "
                    f"{self.status_filter_string}"
                )
                return False
        return True

    def build_events_data(self, alert: Alert) -> [dict]:
        """Build events data out of alert

        Args:
            alert (Alert): Alert dataclass

        Returns:
            [dict]: list of flattened event dicts
        """
        events = [self.build_main_event(alert)]
        events.extend(self.build_object_events(alert))
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

        alert_data.pop("object_refs", None)
        alert_data[alert_data.get("type", "")] = alert_data.get("name", "")

        return dict_to_flat(alert_data)

    def build_object_events(self, alert: Alert) -> [dict]:
        """Build events data out of alert details

        Args:
            alert (Alert): Alert dataclass

        Returns:
            [dict]: list of events flat dicts
        """
        events_data = copy.deepcopy([ev.raw_data for ev in alert.events])
        events = []

        for event in events_data:
            event.pop("object_refs", None)
            event[event.get("type", "")] = event.get("name", "")
            event["fallback_timestamp"] = alert.raw_data.get("modified")
            if event["type"] == constants.COMPROMISE_TARGET_TYPE:
                try:
                    if event["primary_target"][0]["asset_ip_address"]:
                        event["primary_target"][0]["asset_ip_address"] = json.loads(
                            event["primary_target"][0]["asset_ip_address"]
                        )[0]
                # pylint: disable=broad-exception-caught
                except Exception as e:
                    self.logger.info(
                        f"Parsing asset_ip_address field failed. Error {str(e)}"
                    )

            if event["type"] == constants.COM_ALERT_TYPE:
                try:
                    event["timestamp"] = datetime.datetime.strftime(
                        datetime.datetime.strptime(
                            event["timestamp"], constants.BAD_TIME_FORMAT
                        ),
                        constants.TIME_FORMAT,
                    )
                # pylint: disable=broad-exception-caught
                except Exception as e:
                    self.logger.info(f"Parsing timestamp field failed. Error {str(e)}")

            events.append(dict_to_flat(event))

        return events

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
        alert_info.name = alert.name
        alert_info.description = alert.description
        alert_info.device_vendor = constants.DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            alert.raw_flat_data.get(self.params.device_product_field)
            or constants.DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = constants.SEVERITY_MAPPING.get(alert.severity, -1)
        alert_info.rule_generator = f"{constants.DEFAULT_DEVICE_VENDOR}: {alert.name}"
        alert_info.start_time = alert.modified
        alert_info.end_time = alert.modified
        alert_info.environment = self.env_common.get_environment(alert.raw_flat_data)
        alert_info.events = self.build_events_data(alert=alert)

        return alert_info


def main() -> None:
    """main"""
    script_name = constants.INVESTIGATIONS_CONNECTOR
    is_test = is_test_run(sys.argv)
    connector = InvestigationsConnector(script_name, is_test)
    connector.start()


if __name__ == "__main__":
    main()
