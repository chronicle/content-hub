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

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.base.connector import Connector
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_test_run
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core import datamodels
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager


class AlertsConnector(Connector):
    def __init__(self, _is_test: bool) -> None:
        super().__init__(constants.ALERTS_CONNECTOR_NAME, _is_test)
        self.manager: CrowdStrikeManager | None = None

    def validate_params(self) -> None:
        """Validate connector params with param_validator."""

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch", value=self.params.max_alerts_to_fetch
        )

        if self.params.lowest_severity_score_to_fetch is not None:
            self.params.lowest_severity_score_to_fetch = (
                self.param_validator.validate_severity(
                    param_name="Lowest Severity Score To Fetch",
                    severity=self.params.lowest_severity_score_to_fetch,
                    min_limit=constants.ALERTS_CONNECTOR_MIN_SEVERITY,
                    max_limit=constants.ALERTS_CONNECTOR_MAX_SEVERITY,
                    possible_values=list(
                        constants.ALERTS_CONNECTOR_SEVERITY_MAPPING.keys()
                    ),
                )
            )
            if isinstance(self.params.lowest_severity_score_to_fetch, str):
                self.params.lowest_severity_score_to_fetch = (
                    constants.ALERTS_CONNECTOR_SEVERITY_MAPPING[
                        self.params.lowest_severity_score_to_fetch.lower()
                    ]
                )
        if self.params.fallback_severity is not None:
            self.params.fallback_severity = self.param_validator.validate_severity(
                param_name="Fallback Severity",
                severity=self.params.fallback_severity,
                possible_values=[
                    k
                    for k in constants.ALERTS_CONNECTOR_SEVERITY_MAPPING
                    if k != "info"
                ],
            )

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def init_managers(self) -> None:
        self.manager = CrowdStrikeManager(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.verify_ssl,
            logger=self.logger,
            customer_id=self.params.customer_id,
        )

    def get_last_success_time(self, **kwargs) -> int:
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            time_format=UNIX_FORMAT,
            **kwargs,
        )

    def get_alerts(self) -> list[datamodels.AlertDetails]:
        return self.manager.get_alerts(
            severity=self.params.lowest_severity_score_to_fetch,
            start_timestamp=self.context.last_success_timestamp,
            limit=max(constants.DEFAULT_MAX_LIMIT, self.params.max_alerts_to_fetch),
            fetch_idp=False,
            include_hidden_alerts=self.params.include_hidden_alerts,
        )

    def filter_alerts(
        self, fetched_alerts: list[datamodels.AlertDetails]
    ) -> list[datamodels.AlertDetails]:
        return filter_old_alerts(
            self.siemplify, fetched_alerts, self.context.existing_ids, "alert_id"
        )

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        return (
                not self.params.disable_overflow
                and super().is_overflow_alert(alert_info)
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        if len(processed_alerts) >= self.params.max_alerts_to_fetch:
            return True
        return False

    def pass_filters(self, alert: datamodels.AlertDetails) -> bool:
        if alert.product == "idp":
            self.logger.info(
                f"Alert {alert.alert_id} is an Identity Protection alert, skipping ..."
            )
            return False

        return pass_whitelist_filter(
            self.siemplify,
            self.params.use_dynamic_list_as_a_blocklist,
            alert,
            "display_name",
        )

    def process_alert(self, alert: datamodels.AlertDetails) -> datamodels.AlertDetails:
        alert.set_events(case_name_template=self.params.case_name_template)

        return alert

    def store_alert_in_cache(self, processed_alert: datamodels.AlertDetails) -> None:
        self.context.existing_ids.append(processed_alert.alert_id)

    def create_alert_info(self, processed_alert: datamodels.AlertDetails) -> AlertInfo:
        return processed_alert.get_alert_info(
            alert_info=AlertInfo(),
            environment_common=self.env_common,
            display_id_prefix=constants.ALERTS_CONNECTOR_PREFIX,
            device_vendor=constants.ALERTS_CONNECTOR_DEVICE_VENDOR,
            device_product=constants.ALERTS_CONNECTOR_DEVICE_PRODUCT,
            rule_generator=(
                constants.ALERTS_CONNECTOR_RULE_GENERATOR.format(
                    display_name=processed_alert.display_name
                )
            ),
            alert_name_template=self.params.alert_name_template,
            fallback_severity=(
                self.params.fallback_severity.lower()
                if self.params.fallback_severity is not None
                else constants.DEFAULT_FALLBACK_SEVERITY
            ),
        )

    def set_last_success_time(
        self, alerts: list[datamodels.AlertDetails], **kwargs
    ) -> None:
        """Set connector's last success time."""
        super().set_last_success_time(
            alerts=alerts, timestamp_key="created_timestamp", **kwargs
        )

    def write_context_data(self, alerts: list[datamodels.AlertDetails]) -> None:
        """Write connector's context data."""
        if not alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.context.existing_ids)


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = AlertsConnector(is_test)
    connector.start()
