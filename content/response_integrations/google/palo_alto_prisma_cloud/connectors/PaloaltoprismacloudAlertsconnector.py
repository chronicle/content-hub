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
import requests

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.filters import filter_old_alerts, pass_whitelist_filter
from TIPCommon.smp_io import read_ids, write_ids
from TIPCommon.utils import is_test_run
from ..core import AuthenticationManager as auth_manager
from ..core import PaloAltoPrismaCloudManager as api_manager
from ..core import constants
from ..core import datamodels


class AlertsConnector(Connector):
    def __init__(self, _is_test: bool) -> None:
        super().__init__(constants.ALERTS_CONNECTOR_NAME, _is_test)
        self.manager: api_manager.ApiManager | None = None

    def validate_params(self) -> None:
        """Validate connector params with param_validator."""

        self.params.max_hours_backwards = self.param_validator.validate_positive(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

        self.params.max_alerts_to_fetch = self.param_validator.validate_positive(
            param_name="Max Alerts To Fetch", value=self.params.max_alerts_to_fetch
        )

    def _set_auth_api_params(self) -> None:
        self.params.session_auth_params = auth_manager.SessionAuthenticationParameters(
            api_root=self.params.api_root,
            access_key_id=self.params.access_key_id,
            secret_access_key=self.params.secret_access_key,
            verify_ssl=self.params.verify_ssl,
        )
        self.params.api_params = api_manager.ApiParameters(
            api_root=self.params.api_root,
            access_key_id=self.params.access_key_id,
            secret_access_key=self.params.secret_access_key,
            verify_ssl=self.params.verify_ssl,
        )

    def init_managers(self) -> api_manager.ApiManager:
        self._set_auth_api_params()
        session = self._get_authenticated_session()
        self.manager = api_manager.ApiManager(
            session=session, api_parameters=self.params.api_params, logger=self.logger
        )

    def _get_authenticated_session(self) -> requests.Session:
        return auth_manager.get_authenticated_session(self.params.session_auth_params)

    def read_context_data(self) -> None:
        self.logger.info("Reading already existing alerts ids...")
        self.context.existing_ids = read_ids(self.siemplify)

    def get_last_success_time(self, **kwargs) -> int:
        return super().get_last_success_time(
            max_backwards_param_name="max_hours_backwards",
            time_format=UNIX_FORMAT,
            **kwargs,
        )

    def get_alerts(self) -> list[datamodels.AlertResponse.get_alert_info]:
        return self.manager.get_alerts(
            fallback_severity=self.params.lowest_severity_to_fetch,
            max_alerts_to_fetch=self.params.max_alerts_to_fetch,
            max_hours_backwards=self.params.max_hours_backwards,
            last_alert_time=self.context.last_success_timestamp,
        )

    def filter_alerts(
        self, fetched_alerts: list[datamodels.AlertResponse.get_alert_info]
    ) -> list[datamodels.AlertResponse.get_alert_info]:
        return filter_old_alerts(
            self.siemplify, fetched_alerts, self.context.existing_ids, "alert_id"
        )

    def max_alerts_processed(self, processed_alerts: list[AlertInfo]) -> bool:
        if len(processed_alerts) >= self.params.max_alerts_to_fetch:
            return True

        return False

    def pass_filters(self, alert: datamodels.AlertResponse.get_alert_info) -> bool:
        return pass_whitelist_filter(
            self.siemplify, self.params.use_dynamic_list_as_a_blocklist, alert, "name"
        )

    def process_alert(
        self, alert: datamodels.AlertResponse.get_alert_info
    ) -> datamodels.SetAlertdetails.from_json:
        alert.set_events()
        return alert

    def store_alert_in_cache(
        self, processed_alert: datamodels.AlertResponse.get_alert_info
    ) -> None:
        self.context.existing_ids.append(processed_alert.alert_id)

    def create_alert_info(self, processed_alert: datamodels.AlertResponse) -> AlertInfo:
        return processed_alert.get_alert_info(
            alert_info=AlertInfo(), environment_common=self.env_common
        )

    def set_last_success_time(
        self, alerts: list[datamodels.AlertResponse.get_alert_info], **kwargs
    ) -> None:
        """Set connector's last success time."""
        super().set_last_success_time(
            alerts=alerts, timestamp_key="alert_time", **kwargs
        )

    def write_context_data(
        self, alerts: list[datamodels.AlertResponse.get_alert_info]
    ) -> None:
        """Write connector's context data."""
        if not alerts:
            return

        self.logger.info("Saving existing ids.")
        write_ids(self.siemplify, self.context.existing_ids)


if __name__ == "__main__":
    is_test = is_test_run(sys.argv)
    connector = AlertsConnector(is_test)
    connector.start()
