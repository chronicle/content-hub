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

from netskope.actions.ListEvents import main


class TestListEvents:
    """Unit tests for ListEvents action."""

    def test_list_events_with_type_success(self, mock_siemplify: MagicMock) -> None:
        """Test ListEvents with type success.

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
            if param_name == "Type":
                return "page"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "result": [{"_id": "event_1", "type": "page"}],
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 1 events" in args[0]

    def test_list_events_no_type_success(self, mock_siemplify: MagicMock) -> None:
        """Test ListEvents without type success (all events).

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
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            # We have 4 types: page, application, audit, infrastructure.
            # Let's mock 4 responses.
            response1 = MagicMock()
            response1.json.return_value = {
                "ok": 1,
                "result": [{"_id": "event_1", "type": "page"}],
            }
            response2 = MagicMock()
            response2.json.return_value = {
                "ok": 1,
                "result": [{"_id": "event_2", "type": "application"}],
            }
            response3 = MagicMock()
            response3.json.return_value = {"ok": 1, "result": []}
            response4 = MagicMock()
            response4.json.return_value = {"ok": 1, "result": []}

            mock_get.side_effect = [response1, response2, response3, response4]

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 2 events" in args[0]

            # Verify that the first request used the correct limit (100 in this test)
            # and not the default MAX_LIMIT (5000)
            first_call = mock_get.call_args_list[0]
            _, kwargs = first_call
            params = kwargs.get("params", {})
            assert params.get("limit") == 100
