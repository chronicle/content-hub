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
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from collections.abc import Callable

from cyberint.connectors import AlertsConnector


class TestCyberintAlertsConnector(unittest.TestCase):
    """Unit tests for Cyberint Alerts Connector."""

    def setUp(self) -> None:
        """Sets up connector patches and mock alert objects for each test."""
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

        self.mock_siemplify_cls = self.enterContext(
            patch("cyberint.connectors.AlertsConnector.SiemplifyConnectorExecution")
        )
        self.mock_extract_param = self.enterContext(
            patch("cyberint.connectors.AlertsConnector.extract_connector_param")
        )
        self.mock_is_overflowed = self.enterContext(
            patch("cyberint.connectors.AlertsConnector.is_overflowed", return_value=True)
        )
        self.mock_manager_cls = self.enterContext(
            patch("cyberint.connectors.AlertsConnector.CyberintManager")
        )
        self.mock_get_environment_common = self.enterContext(
            patch("cyberint.connectors.AlertsConnector.get_environment_common")
        )
        self.enterContext(
            patch(
                "cyberint.connectors.AlertsConnector.get_last_success_time",
                return_value="2026-08-14T06:00:00Z",
            )
        )
        self.enterContext(
            patch("cyberint.connectors.AlertsConnector.read_ids", return_value=[])
        )
        self.enterContext(patch("cyberint.connectors.AlertsConnector.save_timestamp"))
        self.enterContext(patch("cyberint.connectors.AlertsConnector.write_ids"))
        self.enterContext(
            patch(
                "cyberint.connectors.AlertsConnector.is_approaching_timeout",
                return_value=False,
            )
        )
        self.enterContext(
            patch("cyberint.connectors.AlertsConnector.pass_filters", return_value=True)
        )

        self.mock_siemplify = MagicMock()
        self.mock_siemplify.whitelist = []
        self.mock_siemplify_cls.return_value = self.mock_siemplify

        mock_env = MagicMock()
        mock_env.get_environment.return_value = "Default"
        self.mock_get_environment_common.return_value = mock_env

        mock_manager = MagicMock()
        mock_manager.get_alerts.return_value = [self.mock_alert]
        self.mock_manager_cls.return_value = mock_manager

    def _create_param_side_effect(self, disable_overflow: bool = False) -> Callable[..., object]:
        """Creates a mock side effect function for siemplify.get_connector_context_property."""
        param_map: dict[str, object] = {
            "Disable Overflow": disable_overflow,
            "API Root": "https://test.cyberint.io",
            "API Key": "test-key",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Alerts To Fetch": 100,
            "Use whitelist as a blacklist": False,
            "DeviceProductField": "Product Name",
        }

        def param_side_effect(
            siemplify: MagicMock,
            param_name: str | None = None,
            **kwargs: object,
        ) -> object:
            """Mock parameter retrieval lookup."""
            param = param_name or kwargs.get("param_name")
            if param in param_map:
                return param_map[param]
            return kwargs.get("default_value")

        return param_side_effect

    def test_overflow_alert_skipped_when_disable_overflow_is_false(self) -> None:
        """Test that an alert found to be overflowed is skipped when Disable Overflow is False."""
        self.mock_extract_param.side_effect = self._create_param_side_effect(
            disable_overflow=False
        )

        AlertsConnector.main(is_test_run=False)

        self.mock_is_overflowed.assert_called_once()
        self.mock_siemplify.LOGGER.info.assert_any_call(
            "phishing-alert-123-Default-CyberInt found as overflow alert. Skipping..."
        )

    def test_overflow_alert_processed_when_disable_overflow_is_true(self) -> None:
        """Test that an alert is processed when Disable Overflow is True even if overflow is met."""
        self.mock_extract_param.side_effect = self._create_param_side_effect(
            disable_overflow=True
        )

        AlertsConnector.main(is_test_run=False)

        self.mock_is_overflowed.assert_not_called()
        self.mock_siemplify.LOGGER.info.assert_any_call(
            "phishing-alert-123-Default-CyberInt is processing (overflow protection disabled)."
        )
        self.mock_siemplify.LOGGER.info.assert_any_call("Alert alert-123 was created.")
