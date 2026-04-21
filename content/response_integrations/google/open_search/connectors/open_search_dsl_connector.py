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

import json
import sys
from typing import TYPE_CHECKING

from ..core.constants import (
    DLS_CONNECTOR_NAME,
    INTEGRATION_NAME,
    SEVERITY_MAP,
    STORED_ALERT_IDS_LIMIT,
)
from ..core.data_models import IntegrationParameters
from EnvironmentCommon import GetEnvironmentCommonFactory
from ..core.exceptions import OpenSearchDSLConnectorException
from ..core.os_client import OpenSearchManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon.base.connector import Connector
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.smp_time import unix_now
from TIPCommon.utils import is_overflowed, is_test_run
from ..core.utils import (
    DEFAULT_SEVERITY_VALUE,
    get_field_value,
    load_custom_severity_configuration,
    map_severity_value,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from typing import Any

CONNECTOR_STARTING_TIME = unix_now()


class OpenSearchDSLConnector(Connector):
    """
    OpenSearch DSL Connector for fetching alerts using DSL queries.
    """

    def __init__(self, _is_test: bool) -> None:
        super().__init__(DLS_CONNECTOR_NAME, _is_test)
        self.manager: OpenSearchManager | None = None
        self.environment_common = None

    def validate_params(self):
        """Validate connector parameters."""
        if self.params.query != "*":
            try:
                json.loads(self.params.query)
            except json.JSONDecodeError as e:
                raise OpenSearchDSLConnectorException(
                    "Provide valid json for query"
                ) from e

        if self.params.alert_severity:
            if self.params.alert_severity.upper() in SEVERITY_MAP:
                self.params.alert_severity = SEVERITY_MAP[
                    self.params.alert_severity.upper()
                ]
            else:
                raise OpenSearchDSLConnectorException(
                    "Alert Severity isn't valid value"
                )

    def init_managers(self) -> None:
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
            integration_parameters=integration_parameters,
            logger=self.logger,
        )

        self.environment_common = (
            GetEnvironmentCommonFactory.create_environment_manager(
                self.siemplify,
                self.params.environment_field_name,
                self.params.environment_regex_pattern,
            )
        )

        load_custom_severity_configuration(
            self.siemplify, self.params.severity_field_name
        )

    def read_context_data(self) -> None:
        """Read the connector's context data (existing alert IDs)."""
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self) -> int:
        """Get the last success time for the connector.

        Returns:
            int: A hardcoded value(1) as this connector does not use time-based fetching
        """
        return 1

    def get_alerts(self) -> list:
        """Fetch alerts from OpenSearch using a DSL query.

        Returns:
            list: A list of found alerts, sorted by timestamp. In test mode,
                only the first alert is returned.
        """
        self.logger.info(
            f"Successfully loaded {len(self.context.existing_ids)} existing ids"
        )

        all_alerts, _ = self.manager.dsl_search(
            chronicle_soar=self.siemplify,
            indices=self.params.index,
            query=self.params.query,
            max_results=self.params.alerts_count_limit,
            existing_ids=self.context.existing_ids,
            connector_start_time=CONNECTOR_STARTING_TIME,
            python_process_timeout=self.params.python_process_timeout,
        )

        alerts = sorted(
            all_alerts,
            key=lambda alert: get_field_value(
                alert.to_flat(), self.params.timestamp_field, "0"
            ),
        )

        return alerts[:1] if self.is_test_run else alerts

    def process_alerts(self, alerts: list) -> tuple[list[AlertInfo], list]:
        """Process fetched alerts into Chronicle SOAR AlertInfo objects.

        Args:
            alerts (list): A list of alert objects to process.

        Returns:
            tuple[list[AlertInfo], list]: A tuple containing a list of created
                non-overflowed cases and a list of all processed alert IDs.
        """
        processed_alerts: list[AlertInfo] = []
        all_alerts_ids: list[Any] = []

        for alert in alerts:
            try:
                self.logger.info(f"Processing alert {alert.alert_id}")
                all_alerts_ids.append(alert.alert_id)

                flat_alert = alert.to_flat()
                case: AlertInfo = self.create_alert_info(flat_alert)

                if is_overflowed(self.siemplify, case, self.is_test_run):
                    self.logger.info(
                        f"{case.rule_generator}-{case.ticket_id}-"
                        f"{case.environment}-{case.device_product} "
                        f"found as overflow alert. Skipping."
                    )
                    continue

                processed_alerts.append(case)
                self.context.existing_ids.append(alert.alert_id)

            except (KeyError, ValueError) as e:
                self.logger.error(
                    f"Failed to process alert with id {alert.alert_id}: {e}"
                )
                self.logger.exception(e)
                if self.is_test_run:
                    raise OpenSearchDSLConnectorException(e) from e

        return processed_alerts, all_alerts_ids

    def create_alert_info(self, flat_alert: SingleJson) -> AlertInfo:
        """Create an AlertInfo object from an OpenSearch alert.

        Args:
            flat_alert (SingleJson): A flattened OpenSearch alert.

        Returns:
            AlertInfo: The newly created alert.
        """
        self.logger.info(f"Creating Case for Alert {flat_alert['_id']}")

        try:
            case_info: AlertInfo = AlertInfo()
            name: str = get_field_value(flat_alert, self.params.alert_field_name, "")
            case_info.name = name
            case_info.ticket_id = flat_alert["_id"]
            case_info.rule_generator = name
            case_info.display_id = flat_alert["_id"]
            case_info.device_vendor = INTEGRATION_NAME
            case_info.device_product = get_field_value(
                flat_alert, self.params.device_product_field, ""
            )
            flat_alert[self.params.event_class_id] = get_field_value(
                flat_alert, self.params.event_class_id, ""
            )

            try:
                alert_time: int = convert_string_to_unix_time(
                    get_field_value(flat_alert, self.params.timestamp_field)
                )
            except (ValueError, TypeError) as e:
                self.logger.error(f"Unable to get alert time: {str(e)}")
                self.logger.exception(e)
                alert_time: int = 1

            case_info.start_time = alert_time
            case_info.end_time = alert_time

            flat_alert[self.params.environment_field_name] = get_field_value(
                flat_alert,
                self.params.environment_field_name,
                self.siemplify.context.connector_info.environment,
            )
            case_info.environment = self.environment_common.get_environment(flat_alert)

        except KeyError as e:
            raise KeyError(f"Mandatory key is missing: {e}") from e

        case_info.events = [flat_alert]
        case_info.extensions.update(
            {"OS Index": self.params.index, "OS Query": self.params.query}
        )
        case_info.description = get_field_value(
            flat_alert, self.params.alert_description_field, ""
        )
        if self.params.alert_severity:
            case_info.priority = self.params.alert_severity
        else:
            case_info.priority = map_severity_value(
                self.params.severity_field_name,
                get_field_value(
                    flat_alert, self.params.severity_field_name, DEFAULT_SEVERITY_VALUE
                ),
            )
        return case_info

    def write_context_data(self, all_alerts: list) -> None:
        """Write connector's context data (existing alert IDs).

        Args:
            all_alerts (list): A list of all alerts found in the current run.
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


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = OpenSearchDSLConnector(is_test)
    connector.start()
