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

from ..core.constants import (
    ALERTS_LIMIT,
    OS_CONNECTOR_NAME,
    DEFAULT_DAYS_BACKWARDS,
    INTEGRATION_NAME,
    STORED_ALERT_IDS_LIMIT,
    TIME_FORMAT,
)
from ..core.data_models import IntegrationParameters
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.os_client import OpenSearchManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, convert_unixtime_to_datetime
from TIPCommon.base.connector import Connector
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import get_last_success_time
from TIPCommon.transformation import dict_to_flat
from TIPCommon.utils import is_overflowed, is_test_run
from ..core.utils import (
    DEFAULT_SEVERITY_VALUE,
    get_field_value,
    map_severity_value,
)

if TYPE_CHECKING:
    import datetime

    from typing import Any, Iterable

    from TIPCommon.types import SingleJson


class OpenSearchConnector(Connector):
    """
    OpenSearch Connector
    """

    def __init__(self, _is_test: bool) -> None:
        super().__init__(OS_CONNECTOR_NAME, _is_test)
        self.manager: OpenSearchManager | None = None
        self.environment_common = None

    def validate_params(self) -> None:
        """Validate connector parameters"""
        self.params.alerts_count_limit = self.param_validator.validate_integer(
            param_name="Alerts Count Limit",
            value=getattr(self.params, "alerts_count_limit", None),
            default_value=ALERTS_LIMIT,
        )
        self.params.max_days_backwards = self.param_validator.validate_integer(
            param_name="Max Days Backwards",
            value=getattr(self.params, "max_days_backwards", None),
            default_value=DEFAULT_DAYS_BACKWARDS,
        )

    def init_managers(self) -> OpenSearchManager:
        """Initializes the API client manager."""
        integration_parameters = IntegrationParameters(
            server=self.params.server_address,
            username=self.params.username,
            password=self.params.password,
            jwt_token=self.params.jwt_token,
            verify_ssl=self.params.verify_ssl,
            ca_certificate_file=self.params.ca_certificate_file,
            authenticate=self.params.authenticate,
        )
        self.manager = OpenSearchManager(
            integration_parameters=integration_parameters, logger=self.logger
        )
        self.environment_common = (
            GetEnvironmentCommonFactory.create_environment_manager(
                self.siemplify,
                self.params.environment_field,
                self.params.environment_regex_pattern,
            )
        )
        return self.manager

    def get_alerts(self) -> list:
        """Fetch alerts from OpenSearch.

        Returns:
            list: A list of found alerts.
        """
        last_run_time: datetime.datetime = self.get_last_success_time()
        self.logger.info(f"Querying OS since {last_run_time.isoformat()}")
        all_alerts, _, _ = self.manager.advanced_os_search(
            **{
                "Index": self.params.indexes,
                "Query": self.params.query,
                "Oldest Date": last_run_time.strftime(TIME_FORMAT),
                "Timestamp Field": self.params.timestamp_field,
                "Existing IDs": self.context.existing_ids,
                "Limit": self.params.alerts_count_limit,
            }
        )

        return sorted(
            all_alerts,
            key=lambda alert: get_field_value(
                dict_to_flat(alert), self.params.timestamp_field, 0
            ),
        )

    def create_alert_info(self, flat_alert: SingleJson) -> AlertInfo:
        """Create an AlertInfo object from an OpenSearch alert.

        Args:
            flat_alert (SingleJson): A flattened OpenSearch alert.

        Returns:
            AlertInfo: The created AlertInfo object.
        """
        self.logger.info(
            f"Creating Case for Alert {str(flat_alert['_id']).encode('utf-8')}"
        )

        try:
            case_info: AlertInfo = AlertInfo()

            try:
                name = get_field_value(flat_alert, self.params.alert_name_field)
            except KeyError as e:
                self.logger.error(f"Unable to get alert name: {str(e)}")
                self.logger.exception(e)
                name: str = ""

            case_info.name = name
            case_info.ticket_id = flat_alert["_id"]

            case_info.rule_generator = name
            case_info.display_id = flat_alert["_id"]
            case_info.device_vendor = INTEGRATION_NAME

            case_info.device_product = get_field_value(
                flat_alert, self.params.device_product_field, ""
            )

            timestamp_value = get_field_value(flat_alert, self.params.timestamp_field)

            try:
                alert_time = convert_string_to_unix_time(timestamp_value)
            except ValueError:
                try:
                    timestamp_value = f"{timestamp_value}Z"
                    alert_time = convert_string_to_unix_time(timestamp_value)

                except ValueError as e_inner:
                    self.logger.error(f"Unable to get alert time: {str(e_inner)}")
                    self.logger.exception(e_inner)
                    alert_time = 1

            case_info.start_time = alert_time
            case_info.end_time = alert_time

            if self.params.environment_field:
                flat_alert[self.params.environment_field] = get_field_value(
                    flat_alert,
                    self.params.environment_field,
                    self.siemplify.context.connector_info.environment,
                )
            case_info.environment = self.environment_common.get_environment(flat_alert)

            case_info.priority = map_severity_value(
                self.params.severity_field_name,
                get_field_value(
                    flat_alert, self.params.severity_field_name, DEFAULT_SEVERITY_VALUE
                ),
            )

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {str(e)}") from e

        flat_alert[self.params.event_class_id] = get_field_value(
            flat_alert, self.params.event_class_id, ""
        )

        case_info.events = [flat_alert]
        case_info.extensions.update(
            {"OS Index": self.params.indexes, "OS Query": self.params.query}
        )
        return case_info

    def read_context_data(self) -> None:
        """Read connector's context data."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self) -> Any:
        """Get the connector's last successful run time.

        Returns:
            Any: The last success time.
        """
        return get_last_success_time(
            self.siemplify,
            offset_with_metric={"days": self.params.max_days_backwards},
        )

    def write_context_data(self, all_alerts: Iterable) -> None:
        """Write connector's context data.

        Args:
            all_alerts (Iterable): A list of all alerts found in the current run.
                If empty, no data is written.
        """
        if not all_alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(
            self.siemplify,
            self.context.existing_ids,
            stored_ids_limit=STORED_ALERT_IDS_LIMIT,
        )

    def process_alerts(
        self,
        alerts: Iterable,
    ) -> tuple[list[AlertInfo], list]:
        """Process fetched alerts into Siemplify CaseInfo objects.

        Args:
            alerts (Iterable): An iterable of alerts to process.

        Returns:
            tuple[list[AlertInfo], list]: A tuple containing a list of created
                non-overflowed cases and a list of all created cases.
        """
        cases: list[AlertInfo] = []
        all_cases: list[AlertInfo] = []

        for alert in alerts:
            try:
                flat_alert: SingleJson = dict_to_flat(alert)

                case = self.create_alert_info(flat_alert)
                self.logger.info(
                    "Alert timestamp: "
                    f"{convert_unixtime_to_datetime(case.start_time).isoformat()}"
                )
                self.context.existing_ids.append(alert["_id"])
                all_cases.append(case)

                if is_overflowed(self.siemplify, case, self.is_test_run):
                    self.logger.info(
                        f"{str(case.rule_generator)}-"
                        f"{str(case.ticket_id)}-{str(case.environment)}-"
                        f"{str(case.device_product)} found as overflow alert. Skipping."
                    )
                    continue

                cases.append(case)
                if (
                    self.params.alerts_count_limit
                    and len(cases) >= self.params.alerts_count_limit
                ):
                    self.logger.info("Reached alerts limit per cycle.")
                    break

            except (KeyError, ValueError) as e:
                self.logger.error(
                    f"Failed to create CaseInfo for alert {alert['_id']}: {str(e)}"
                )
                self.logger.error(f"Error Message: {str(e)}")
                if self.is_test_run:
                    raise

        self.logger.info(
            f"Found total {len(all_cases)} cases, non-overflowed cases: {len(cases)}"
        )
        return cases, all_cases


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = OpenSearchConnector(is_test)
    connector.start()
