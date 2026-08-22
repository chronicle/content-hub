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

import unittest
from unittest.mock import MagicMock, patch

from cyberint.connectors import AlertsConnector


class TestCyberintAlertsConnector(unittest.TestCase):
    """Unit tests for Cyberint Alerts Connector."""

    def setUp(self) -> None:
        self.mock_alert = MagicMock()
        self.mock_alert.id = "alert-123"
        self.mock_alert.title = "Test Alert"
        self.mock_alert.description = "Test alert description"
        self.mock_alert.severity = "high"
        self.mock_alert.type = "phishing"
        self.mock_alert.created_date = "2026-08-14T07:00:00"
        self.mock_alert.rule_generator = "TestRule"
        self.mock_alert.ticket_id = "123"
        self.mock_alert.environment = "Default Environment"
        self.mock_alert.device_product = "Cyberint"
        self.mock_alert.as_event.return_value = {"event": "data"}
        mock_alert_info = MagicMock()
        mock_alert_info.rule_generator = "phishing"
        mock_alert_info.ticket_id = "alert-123"
        mock_alert_info.environment = "Default"
        mock_alert_info.device_product = "CyberInt"
        self.mock_alert.get_alert_info.return_value = mock_alert_info

    @patch("cyberint.connectors.AlertsConnector.get_environment_common")
    @patch("cyberint.connectors.AlertsConnector.write_ids")
    @patch("cyberint.connectors.AlertsConnector.save_timestamp")
    @patch("cyberint.connectors.AlertsConnector.read_ids", return_value=[])
    @patch("cyberint.connectors.AlertsConnector.get_last_success_time", return_value="2026-08-14T06:00:00Z")
    @patch("cyberint.connectors.AlertsConnector.CyberintManager")
    @patch("cyberint.connectors.AlertsConnector.is_overflowed", return_value=True)
    @patch("cyberint.connectors.AlertsConnector.extract_connector_param")
    @patch("cyberint.connectors.AlertsConnector.SiemplifyConnectorExecution")
    def test_overflow_alert_skipped_when_disable_overflow_is_false(
        self,
        mock_siemplify_cls,
        mock_extract_param,
        mock_is_overflowed,
        mock_manager_cls,
        mock_last_success_time,
        mock_read_ids,
        mock_save_timestamp,
        mock_write_ids,
        mock_get_environment_common,
    ) -> None:
        """Test that an alert found to be overflowed is skipped when Disable Overflow is False."""
        mock_siemplify = MagicMock()
        mock_siemplify.whitelist = []
        mock_siemplify_cls.return_value = mock_siemplify

        mock_env = MagicMock()
        mock_env.get_environment.return_value = "Default"
        mock_get_environment_common.return_value = mock_env

        mock_manager = MagicMock()
        mock_manager.get_alerts.return_value = [self.mock_alert]
        mock_manager_cls.return_value = mock_manager

        def param_side_effect(siemplify, param_name=None, **kwargs):
            param = param_name or kwargs.get("param_name")
            if param == "Disable Overflow":
                return False
            if param == "API Root":
                return "https://test.cyberint.io"
            if param == "API Key":
                return "test-key"
            if param == "Verify SSL":
                return True
            if param == "PythonProcessTimeout":
                return 180
            if param == "Max Hours Backwards":
                return 1
            if param == "Max Alerts To Fetch":
                return 100
            if param == "Use whitelist as a blacklist":
                return False
            if param == "DeviceProductField":
                return "Product Name"
            return kwargs.get("default_value")

        mock_extract_param.side_effect = param_side_effect

        with patch("cyberint.connectors.AlertsConnector.is_approaching_timeout", return_value=False):
            with patch("cyberint.connectors.AlertsConnector.pass_filters", return_value=True):
                AlertsConnector.main(is_test_run=False)

        mock_is_overflowed.assert_called_once()
        mock_siemplify.LOGGER.info.assert_any_call(
            "phishing-alert-123-Default-CyberInt found as overflow alert. Skipping..."
        )

    @patch("cyberint.connectors.AlertsConnector.get_environment_common")
    @patch("cyberint.connectors.AlertsConnector.write_ids")
    @patch("cyberint.connectors.AlertsConnector.save_timestamp")
    @patch("cyberint.connectors.AlertsConnector.read_ids", return_value=[])
    @patch("cyberint.connectors.AlertsConnector.get_last_success_time", return_value="2026-08-14T06:00:00Z")
    @patch("cyberint.connectors.AlertsConnector.CyberintManager")
    @patch("cyberint.connectors.AlertsConnector.is_overflowed", return_value=True)
    @patch("cyberint.connectors.AlertsConnector.extract_connector_param")
    @patch("cyberint.connectors.AlertsConnector.SiemplifyConnectorExecution")
    def test_overflow_alert_processed_when_disable_overflow_is_true(
        self,
        mock_siemplify_cls,
        mock_extract_param,
        mock_is_overflowed,
        mock_manager_cls,
        mock_last_success_time,
        mock_read_ids,
        mock_save_timestamp,
        mock_write_ids,
        mock_get_environment_common,
    ) -> None:
        """Test that an alert is processed when Disable Overflow is True even if overflow condition is met."""
        mock_siemplify = MagicMock()
        mock_siemplify.whitelist = []
        mock_siemplify_cls.return_value = mock_siemplify

        mock_env = MagicMock()
        mock_env.get_environment.return_value = "Default"
        mock_get_environment_common.return_value = mock_env

        mock_manager = MagicMock()
        mock_manager.get_alerts.return_value = [self.mock_alert]
        mock_manager_cls.return_value = mock_manager

        def param_side_effect(siemplify, param_name=None, **kwargs):
            param = param_name or kwargs.get("param_name")
            if param == "Disable Overflow":
                return True
            if param == "API Root":
                return "https://test.cyberint.io"
            if param == "API Key":
                return "test-key"
            if param == "Verify SSL":
                return True
            if param == "PythonProcessTimeout":
                return 180
            if param == "Max Hours Backwards":
                return 1
            if param == "Max Alerts To Fetch":
                return 100
            if param == "Use whitelist as a blacklist":
                return False
            if param == "DeviceProductField":
                return "Product Name"
            return kwargs.get("default_value")

        mock_extract_param.side_effect = param_side_effect

        with patch("cyberint.connectors.AlertsConnector.is_approaching_timeout", return_value=False):
            with patch("cyberint.connectors.AlertsConnector.pass_filters", return_value=True):
                AlertsConnector.main(is_test_run=False)

        mock_is_overflowed.assert_called_once()
        mock_siemplify.LOGGER.info.assert_any_call(
            "phishing-alert-123-Default-CyberInt found as overflow alert, but overflow is disabled. Processing..."
        )
        mock_siemplify.LOGGER.info.assert_any_call("Alert alert-123 was created.")


if __name__ == "__main__":
    unittest.main()
