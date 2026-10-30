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
from collections import OrderedDict

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.base.connector import Connector
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.extraction import extract_connector_param
from TIPCommon.filters import pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_test_run

from crowd_strike_falcon.core.constants import (
    INCIDENTS_CONNECTOR_NAME,
    INCIDENTS_CONNECTOR_MIN_INCIDENTS_TO_FETCH,
    INCIDENTS_CONNECTOR_MAX_INCIDENTS_TO_FETCH,
    INCIDENTS_CONNECTOR_SEVERITY_MIN_VAL,
    INCIDENTS_CONNECTOR_SEVERITY_MAX_VAL,
    INCIDENTS_CONNECTOR_SEVERITY_MAPPING,
    API_ROOT_DEFAULT,
    INCIDENTS_CONNECTOR_DEFAULT_INCIDENTS_TO_FETCH,
    INCIDENTS_CONNECTOR_DEFAULT_MAX_HOURS_BACKWARDS,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core import datamodels


class IncidentsConnector(Connector):
    def __init__(self, _is_test: bool) -> None:
        super().__init__(INCIDENTS_CONNECTOR_NAME, _is_test)
        self.manager: CrowdStrikeManager | None = None

    def extract_params(self):
        self.params.api_root = extract_connector_param(
            self.siemplify,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
            default_value=API_ROOT_DEFAULT,
        )

        self.params.client_id = extract_connector_param(
            self.siemplify, param_name="Client ID", is_mandatory=True, print_value=True
        )

        self.params.customer_id = extract_connector_param(
            self.siemplify, param_name="Customer ID", print_value=True
        )

        self.params.client_secret = extract_connector_param(
            self.siemplify, param_name="Client Secret", is_mandatory=True
        )

        self.params.verify_ssl = extract_connector_param(
            self.siemplify,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
            print_value=True,
            default_value=False,
        )

        self.params.max_incidents_to_fetch = extract_connector_param(
            self.siemplify,
            param_name="Max Incidents To Fetch",
            print_value=True,
            default_value=INCIDENTS_CONNECTOR_DEFAULT_INCIDENTS_TO_FETCH,
        )

        self.params.max_hours_backwards = extract_connector_param(
            self.siemplify,
            param_name="Max Hours Backwards",
            print_value=True,
            default_value=INCIDENTS_CONNECTOR_DEFAULT_MAX_HOURS_BACKWARDS,
        )

        self.params.lowest_severity_score_to_fetch = extract_connector_param(
            self.siemplify,
            param_name="Lowest Severity Score To Fetch",
            print_value=True,
        )

        self.params.use_dynamic_list_as_a_blocklist = extract_connector_param(
            self.siemplify,
            param_name="Use dynamic list as a blocklist",
            input_type=bool,
            is_mandatory=True,
            print_value=True,
            default_value=False,
        )

        self.params.environment_field_name = extract_connector_param(
            self.siemplify, param_name="Environment Field Name", print_value=True
        )

        self.params.environment_regex_pattern = extract_connector_param(
            self.siemplify, param_name="Environment Regex Pattern", print_value=True
        )

        self.params.python_process_timeout = extract_connector_param(
            self.siemplify,
            param_name="PythonProcessTimeout",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

        self.params.disable_overflow = extract_connector_param(
            self.siemplify,
            param_name="Disable Overflow",
            input_type=bool,
            default_value=False,
            print_value=True,
        )

    def validate_params(self) -> None:
        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

        self.params.max_incidents_to_fetch = self.param_validator.validate_range(
            param_name="Max Incidents To Fetch",
            value=self.params.max_incidents_to_fetch,
            min_limit=INCIDENTS_CONNECTOR_MIN_INCIDENTS_TO_FETCH,
            max_limit=INCIDENTS_CONNECTOR_MAX_INCIDENTS_TO_FETCH,
        )

        if self.params.lowest_severity_score_to_fetch:
            self.params.lowest_severity_score_to_fetch = (
                self.param_validator.validate_severity(
                    param_name="Lowest Severity Score To Fetch",
                    severity=self.params.lowest_severity_score_to_fetch,
                    min_limit=INCIDENTS_CONNECTOR_SEVERITY_MIN_VAL,
                    max_limit=INCIDENTS_CONNECTOR_SEVERITY_MAX_VAL,
                    possible_values=list(INCIDENTS_CONNECTOR_SEVERITY_MAPPING.keys()),
                )
            )
            if (
                isinstance(self.params.lowest_severity_score_to_fetch, str)
                and self.params.lowest_severity_score_to_fetch.lower()
                in INCIDENTS_CONNECTOR_SEVERITY_MAPPING
            ):
                self.params.lowest_severity_score_to_fetch = (
                    INCIDENTS_CONNECTOR_SEVERITY_MAPPING.get(
                        self.params.lowest_severity_score_to_fetch.lower()
                    )
                )

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = OrderedDict(read_ids(siemplify=self.siemplify))

    def init_managers(self) -> None:
        self.manager = CrowdStrikeManager(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.verify_ssl,
            logger=self.logger,
            customer_id=self.params.customer_id,
        )

    def get_last_success_time(self) -> (any, int):
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards", time_format=UNIX_FORMAT
        )

    def get_alerts(self) -> list[datamodels.IncidentDetails]:
        fetched_alerts = self.manager.get_incidents(
            severity=self.params.lowest_severity_score_to_fetch,
            last_success_datetime=self.context.last_success_timestamp,
            limit=max(
                INCIDENTS_CONNECTOR_MAX_INCIDENTS_TO_FETCH,
                self.params.max_incidents_to_fetch,
            ),
        )
        for alert in fetched_alerts:
            alert.behavior_ids = self.manager.get_incident_behaviors(alert.incident_id)

        return fetched_alerts

    def filter_alerts(
        self, fetched_alerts: list[datamodels.IncidentDetails]
    ) -> list[datamodels.IncidentDetails]:
        filtered_alerts = []
        for alert in fetched_alerts:
            if alert.alert_id in self.context.existing_ids:
                if self.context.existing_ids[alert.alert_id] - 1 != len(
                    alert.behavior_ids
                ):
                    filtered_alerts.append(alert)
                    continue

            if alert.alert_id not in self.context.existing_ids:
                filtered_alerts.append(alert)
                continue

            self.logger.info(
                f"The alert {alert.alert_id} skipped since it has been fetched"
                " before"
            )

        return filtered_alerts

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return (
                not self.params.disable_overflow
                and super().is_overflow_alert(alert_info)
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        if len(processed_alerts) >= self.params.max_incidents_to_fetch:
            return True

    def pass_filters(self, alert: datamodels.IncidentDetails) -> bool:
        return pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            alert,
            "incident_type",
        )

    def process_alert(
        self, alert: datamodels.IncidentDetails
    ) -> datamodels.IncidentDetails:
        behaviors = self.manager.get_incident_behaviors_details(alert.behavior_ids)
        alert.set_events(behaviors)
        return alert

    def store_alert_in_cache(self, processed_alert: datamodels.IncidentDetails) -> None:
        if processed_alert.alert_id in self.context.existing_ids:
            del self.context.existing_ids[processed_alert.alert_id]
        self.context.existing_ids[processed_alert.alert_id] = (
            len(processed_alert.behavior_ids) + 1
        )

    def create_alert_info(
        self, processed_alert: datamodels.IncidentDetails
    ) -> AlertInfo:
        return processed_alert.get_alert_info(
            alert_info=AlertInfo(), environment_common=self.env_common
        )

    def set_last_success_time(self, alerts: list[datamodels.IncidentDetails]) -> None:
        super().set_last_success_time(alerts=alerts, timestamp_key="end_time")

    def write_context_data(self, alerts: list[datamodels.IncidentDetails]) -> None:
        if not alerts:
            return
        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, list(self.context.existing_ids.items()))


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = IncidentsConnector(is_test)
    connector.start()
