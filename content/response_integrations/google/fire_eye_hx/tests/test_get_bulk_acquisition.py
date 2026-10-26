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
from unittest.mock import patch

from ..actions import GetBulkAcquisition as get_module


class TestGetBulkAcquisition(unittest.TestCase):
    @patch.object(get_module, "FireEyeHXManager")
    @patch.object(get_module, "extract_action_param")
    @patch.object(get_module, "extract_configuration_param")
    @patch.object(get_module, "SiemplifyAction")
    def test_get_bulk_acquisition_success(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.get_bulk_acquisition.return_value = {
            "_id": 42,
            "state": "COMPLETE",
            "progress": {"total": 100, "complete": 100},
        }

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Bulk Acquisition ID":
                return "42"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_module.main()

        mock_manager.get_bulk_acquisition.assert_called_once_with("42")
        mock_siemplify.result.add_result_json.assert_called_once()
        mock_siemplify.end.assert_called_once_with(
            "Successfully retrieved bulk acquisition 42. State: COMPLETE",
            "COMPLETE",
            0,
        )

    @patch.object(get_module, "FireEyeHXManager")
    @patch.object(get_module, "extract_action_param")
    @patch.object(get_module, "extract_configuration_param")
    @patch.object(get_module, "SiemplifyAction")
    def test_get_bulk_acquisition_empty_id_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Bulk Acquisition ID":
                return ""
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_module.main()

        mock_manager.get_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "must not be empty" in end_call[0]
        assert end_call[2] == 2


if __name__ == "__main__":
    unittest.main()
