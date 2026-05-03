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

from netskope.actions.DownloadFile import main


class TestDownloadFile:
    """Unit tests for DownloadFile action."""

    def test_download_file_v2_success(self, mock_siemplify: MagicMock) -> None:
        """Test DownloadFile with V2 success.

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
            if param_name == "File ID":
                return "file_123"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            # First call to get_quarantined_files
            response_list = MagicMock()
            response_list.json.return_value = {
                "ok": 1,
                "quarantineIncidents": [
                    {
                        "id": "file_123",
                        "file_name": "test.txt",
                        "quarantinedResource": {
                            "id": "file_123",
                            "app": "app1",
                            "instance": "inst1",
                        },
                    }
                ],
            }

            # Second call to download_file (binary content)
            response_download = MagicMock()
            response_download.content = b"file content"
            response_download.status_code = 200

            mock_get.side_effect = [response_list, response_download]

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully downloaded file" in args[0]

    def test_download_file_v1_success(self, mock_siemplify: MagicMock) -> None:
        """Test DownloadFile with V1 success.

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
            if param_name == "File ID":
                return "file_123"
            if param_name == "Quarantine Profile ID":
                return "profile_123"
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        with patch("requests.Session.request") as mock_get:
            # First call to get_quarantined_files (V1 format)
            response_list = MagicMock()
            response_list.json.return_value = {
                "status": "success",
                "data": {
                    "quarantined": [
                        {
                            "quarantine_profile_id": "profile_123",
                            "files": [{"id": "file_123", "file_name": "test.txt"}],
                        }
                    ]
                },
            }

            # Second call to download_file
            response_download = MagicMock()
            response_download.history = [MagicMock()]  # To satisfy if response.history:
            response_download.url = "https://redirect-url.com"

            response_final = MagicMock()
            response_final.content = b"file content"
            response_final.status_code = 200

            mock_get.side_effect = [response_list, response_download, response_final]

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully downloaded file" in args[0]
