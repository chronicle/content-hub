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

from netskope.actions.Ping import main


class TestPing:
    """Unit tests for Ping action."""

    def test_ping_v1_success(self, mock_siemplify: MagicMock) -> None:
        """Test Ping with V1 config.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V1 Api Key":
                return "v1_key"
            if param_name == "Verify SSL":
                return True
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "success",
                "data": [],
            }
            mock_get.return_value = mock_response

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Connected successfully" in args[0]

    def test_ping_v2_success(self, mock_siemplify: MagicMock) -> None:
        """Test Ping with V2 config.

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

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "result": [],
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Connected successfully" in args[0]

    def test_ping_missing_config(self, mock_siemplify: MagicMock) -> None:
        """Test Ping with missing config.

        Args:
            mock_siemplify (MagicMock): mock siemplify object.

        Returns:
            None
        """

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "Verify SSL":
                return True
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect

        main()

        mock_siemplify.end.assert_called_once()
        args, _ = mock_siemplify.end.call_args
        assert "Either V1 or V2 API Key needs to be provided" in args[0]
