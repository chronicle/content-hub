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
from netskope.actions.DeployURLListChanges import main


class TestDeployURLListChanges:
    """Unit tests for DeployURLListChanges action."""

    def test_deploy_url_list_changes_success(self, mock_siemplify: MagicMock) -> None:
        """Test DeployURLListChanges success.

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

        with patch("requests.Session.request") as mock_post:
            mock_post.return_value.status_code = 200

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully deployed pending Netskope policy changes" in args[0]
