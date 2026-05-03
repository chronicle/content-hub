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

from soar_sdk.SiemplifyDataModel import EntityTypes

from netskope.actions.AddEntitiesToURLList import main


class TestAddEntitiesToURLList:
    """Unit tests for AddEntitiesToURLList action."""

    def test_add_entities_from_input_success(self, mock_siemplify: MagicMock) -> None:
        """Test AddEntitiesToURLList with input entries success.

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
            if param_name == "URL List Name":
                return "WhiteList"
            if param_name == "Entries":
                return "test1.com,test2.com"
            if param_name == "Deploy URL List Changes":
                return False
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect
        mock_siemplify.target_entities = []

        with patch("requests.Session.request") as mock_request:
            # Mock get_url_list_data
            response_get = MagicMock()
            response_get.json.return_value = [
                {"id": 1, "name": "WhiteList", "data": {"type": "exact"}}
            ]

            # Mock append_to_url_list
            response_patch = MagicMock()
            response_patch.json.return_value = {
                "modify_by": "user",
                "modify_time": "now",
            }

            def request_side_effect(method, _url, **_kwargs):
                if method.upper() == "GET":
                    return response_get
                if method.upper() == "PATCH":
                    return response_patch
                return MagicMock()

            mock_request.side_effect = request_side_effect

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully added the following entities" in args[0]

    def test_add_entities_from_target_success(self, mock_siemplify: MagicMock) -> None:
        """Test AddEntitiesToURLList with target entities success.

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
            if param_name == "URL List Name":
                return "WhiteList"
            if param_name == "Deploy URL List Changes":
                return False
            return default

        mock_siemplify.get_configuration().get.side_effect = get_config_side_effect
        mock_siemplify.parameters.get.side_effect = get_action_param_side_effect

        # Mock target entities
        entity1 = MagicMock()
        entity1.entity_type = EntityTypes.URL
        entity1.identifier = "target1.com"
        mock_siemplify.target_entities = [entity1]

        with patch("requests.Session.request") as mock_request:
            response_get = MagicMock()
            response_get.json.return_value = [
                {"id": 1, "name": "WhiteList", "data": {"type": "exact"}}
            ]

            response_patch = MagicMock()
            response_patch.json.return_value = {
                "modify_by": "user",
                "modify_time": "now",
            }

            def request_side_effect(method, _url, **_kwargs):
                if method.upper() == "GET":
                    return response_get
                if method.upper() == "PATCH":
                    return response_patch
                return MagicMock()

            mock_request.side_effect = request_side_effect

            main()

            mock_siemplify.end.assert_called_once()
            args, _ = mock_siemplify.end.call_args
            assert "Successfully added the following entities" in args[0]
            assert "target1.com" in args[0]
