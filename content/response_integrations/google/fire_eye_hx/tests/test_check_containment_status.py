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

from ..actions import CheckContainmentStatus as check_status_module


class TestCheckContainmentStatus(unittest.TestCase):
    @patch.object(check_status_module, "FireEyeHXManager")
    @patch.object(check_status_module, "extract_action_param")
    @patch.object(check_status_module, "extract_configuration_param")
    @patch.object(check_status_module, "SiemplifyAction")
    def test_check_containment_status_normal(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_host = MagicMock()
        mock_host.raw_data = {"_id": "test-agent-123", "hostname": "TEST-HOST"}
        mock_host.containment_state = "normal"
        mock_manager.get_host_by_agent_id.return_value = mock_host
        mock_manager.resolve_agent_id_from_entities.return_value = "test-agent-123"
        mock_manager.get_containment_status.return_value = {"state": "normal"}

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "test-agent-123"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        check_status_module.main()

        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "test-agent-123" in json_result["operation_results"]
        assert json_result["operation_results"]["test-agent-123"]["result"] == "success"
        assert json_result["operation_results"]["test-agent-123"]["status"] == "uncontained"
        assert json_result["device_metadata"] == {"_id": "test-agent-123", "hostname": "TEST-HOST"}
        mock_siemplify.end.assert_called_once_with(
            "Host with Agent ID test-agent-123 containment status: uncontained",
            "uncontained",
            0,
        )

    @patch.object(check_status_module, "FireEyeHXManager")
    @patch.object(check_status_module, "extract_action_param")
    @patch.object(check_status_module, "extract_configuration_param")
    @patch.object(check_status_module, "SiemplifyAction")
    def test_check_containment_status_contained(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_host = MagicMock()
        mock_host.raw_data = {"_id": "test-agent-456", "hostname": "TEST-HOST-2"}
        mock_host.containment_state = "contained"
        mock_manager.get_host_by_agent_id.return_value = mock_host
        mock_manager.resolve_agent_id_from_entities.return_value = "test-agent-456"
        mock_manager.get_containment_status.return_value = {"state": "contained"}

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "test-agent-456"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        check_status_module.main()

        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["operation_results"]["test-agent-456"]["status"] == "contained"
        mock_siemplify.end.assert_called_once_with(
            "Host with Agent ID test-agent-456 containment status: contained",
            "contained",
            0,
        )

    @patch.object(check_status_module, "FireEyeHXManager")
    @patch.object(check_status_module, "extract_action_param")
    @patch.object(check_status_module, "extract_configuration_param")
    @patch.object(check_status_module, "SiemplifyAction")
    def test_check_containment_status_address_entity(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_entity = MagicMock()
        mock_entity.identifier = "10.0.0.50"
        mock_entity.entity_type = "ADDRESS"
        mock_siemplify.target_entities = [mock_entity]

        mock_host = MagicMock()
        mock_host.raw_data = {"_id": "resolved-ip-agent-999", "primary_ip_address": "10.0.0.50"}
        mock_host.containment_state = "contained"
        mock_manager.get_host_by_agent_id.return_value = mock_host
        mock_manager.resolve_agent_id_from_entities.return_value = "resolved-ip-agent-999"
        mock_manager.get_containment_status.return_value = {"state": "contained"}

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return ""
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        check_status_module.main()

        mock_manager.resolve_agent_id_from_entities.assert_called_once_with(
            target_entities=[mock_entity],
            agent_id_param="",
        )
        mock_siemplify.end.assert_called_once_with(
            "Host with Agent ID resolved-ip-agent-999 containment status: contained",
            "contained",
            0,
        )


if __name__ == "__main__":
    unittest.main()
