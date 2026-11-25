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
from typing import Any
from unittest.mock import MagicMock, patch
from netskope.actions.ListAlerts import main


class TestListAlerts:
    """Unit tests for ListAlerts action."""

    def test_list_alerts_success(self, mock_siemplify: MagicMock) -> None:
        """Test ListAlerts success scenario.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Limit":
                return 100
            if param_name == "Is Acknowledged":
                return False
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "result": [{"_id": "alert_1", "type": "anomaly"}],
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 1 alerts" in args[0]
            mock_siemplify.result.add_data_table.assert_called_once()

    def test_list_alerts_no_data(self, mock_siemplify: MagicMock) -> None:
        """Test ListAlerts with no data found.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Limit":
                return 100
            if param_name == "Is Acknowledged":
                return False
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {"ok": 1, "result": []}

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 0 alerts" in args[0]

    def test_list_alerts_invalid_type(self, mock_siemplify: MagicMock) -> None:
        """Test ListAlerts with invalid type.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Type":
                return "invalid_type"
            if param_name == "Limit":
                return 100
            if param_name == "Is Acknowledged":
                return False
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        main()

        mock_siemplify.end.assert_called_once()
        args, _ = mock_siemplify.end.call_args
        assert "Invalid Alert Type" in args[0]
