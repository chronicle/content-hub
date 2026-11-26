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

from netskope.actions.ListQuarantinedFiles import main


class TestListQuarantinedFiles:
    """Unit tests for ListQuarantinedFiles action."""

    def test_list_quarantined_files_v2_success(self, mock_siemplify: MagicMock) -> None:
        """Test ListQuarantinedFiles with V2 success.

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
            if param_name == "Use V2 API":
                return True
            if param_name == "Max Items To Return":
                return 10
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [{"_id": "file_1", "file_name": "test.txt"}],
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 1 quarantined files" in args[0]

    def test_list_quarantined_files_v1_success(self, mock_siemplify: MagicMock) -> None:
        """Test ListQuarantinedFiles with V1 success.

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

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return False
            if param_name == "Max Items To Return":
                return 10
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "status": "success",
                "data": {
                    "quarantined": [
                        {
                            "quarantine_profile_id": "profile_1",
                            "files": [{"_id": "file_1", "file_name": "test.txt"}],
                        }
                    ]
                },
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 1 quarantined files" in args[0]

    def test_list_quarantined_files_v2_limit_param(
        self, mock_siemplify: MagicMock
    ) -> None:
        """Test ListQuarantinedFiles with V2 verifies the limit param sent to API.

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
            if param_name == "Use V2 API":
                return True
            if param_name == "Max Items To Return":
                return 2
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [{"_id": "file_1", "file_name": "test.txt"}],
            }

            main()

            mock_siemplify.end.assert_called_once()
            # Verify that requests.get was called with limit=2
            called_with_params = mock_get.call_args[1].get("params")
            assert called_with_params is not None
            assert called_with_params.get("limit") == 2

    def test_list_quarantined_files_v1_unset_limit(
        self, mock_siemplify: MagicMock
    ) -> None:
        """Test ListQuarantinedFiles with V1 and unset limit."""

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V1 Api Key":
                return "v1_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return False
            if param_name == "Max Items To Return":
                return None
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "status": "success",
                "data": {
                    "quarantined": [
                        {
                            "quarantine_profile_id": "profile_1",
                            "files": [{"_id": "file_1", "file_name": "test.txt"}],
                        }
                    ]
                },
            }

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Found 1 quarantined files" in args[0]

    def test_list_quarantined_files_v2_unset_limit_default(
        self, mock_siemplify: MagicMock
    ) -> None:
        """Test ListQuarantinedFiles with V2 and unset limit (defaults to 100)."""

        def get_config_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Api Root":
                return "https://test.com"
            if param_name == "V2 Api Key":
                return "v2_key"
            if param_name == "Verify SSL":
                return True
            return default

        def get_action_param_side_effect(param_name: str, default: Any = None) -> Any:
            if param_name == "Use V2 API":
                return True
            if param_name == "Max Items To Return":
                return None
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            mock_get.return_value.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [{"_id": "file_1", "file_name": "test.txt"}],
            }

            main()

            mock_siemplify.end.assert_called_once()
            called_with_params: dict[str, Any] | None = mock_get.call_args[1].get(
                "params"
            )
            assert called_with_params is not None
            assert called_with_params.get("limit") == 100
