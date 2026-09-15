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

from ..actions import CancelHostContain as cancel_host_module


class TestCancelHostContain(unittest.TestCase):
    @patch.object(cancel_host_module, "FireEyeHXManager")
    @patch.object(cancel_host_module, "extract_action_param")
    @patch.object(cancel_host_module, "extract_configuration_param")
    @patch.object(cancel_host_module, "SiemplifyAction")
    def test_cancel_host_contain_by_agent_id_success(
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
        mock_manager.get_host_by_agent_id.return_value = mock_host

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "test-agent-123"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        cancel_host_module.main()

        mock_manager.cancel_containment_by_id.assert_called_once_with("test-agent-123")
        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "test-agent-123" in json_result["operation_results"]
        assert json_result["operation_results"]["test-agent-123"]["result"] == "success"
        assert json_result["operation_results"]["test-agent-123"]["status"] == "uncontained"
        assert json_result["device_metadata"] == {"_id": "test-agent-123", "hostname": "TEST-HOST"}
        mock_siemplify.end.assert_called_once_with(
            "Successfully created cancel contain host task for Agent ID: test-agent-123",
            "true",
            0,
        )

    @patch.object(cancel_host_module, "FireEyeHXManager")
    @patch.object(cancel_host_module, "extract_action_param")
    @patch.object(cancel_host_module, "extract_configuration_param")
    @patch.object(cancel_host_module, "SiemplifyAction")
    def test_cancel_host_contain_by_agent_id_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_host_by_agent_id.side_effect = Exception("Not found")
        mock_manager.cancel_containment_by_id.side_effect = Exception("API error")

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "test-agent-123"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        cancel_host_module.main()

        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "test-agent-123" in json_result["operation_results"]
        assert json_result["operation_results"]["test-agent-123"]["result"] == "failure"
        assert json_result["operation_results"]["test-agent-123"]["status"] == "failed"
        mock_siemplify.end.assert_called_once_with(
            "Failed to cancel contain host with Agent ID: test-agent-123. Error: API error",
            "false",
            2,
        )

    @patch.object(cancel_host_module, "FireEyeHXManager")
    @patch.object(cancel_host_module, "extract_action_param")
    @patch.object(cancel_host_module, "extract_configuration_param")
    @patch.object(cancel_host_module, "SiemplifyAction")
    def test_cancel_host_contain_by_entities_success(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_entity = MagicMock()
        mock_entity.identifier = "TEST-ENDPOINT-01"
        mock_entity.entity_type = "HOSTNAME"
        mock_siemplify.target_entities = [mock_entity]
        mock_siemplify.execution_deadline_unix_time_ms = 9999999999999

        mock_host = MagicMock()
        mock_host._id = "agent-entity-456"
        mock_host.last_poll_timestamp = 1000
        mock_host.raw_data = {"_id": "agent-entity-456", "hostname": "TEST-ENDPOINT-01"}
        mock_manager.get_hosts.return_value = [mock_host]

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return ""
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        cancel_host_module.main()

        mock_manager.cancel_containment_by_id.assert_called_once_with("agent-entity-456")
        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "TEST-ENDPOINT-01" in json_result["operation_results"]
        assert json_result["operation_results"]["TEST-ENDPOINT-01"]["result"] == "success"
        assert json_result["operation_results"]["TEST-ENDPOINT-01"]["status"] == "uncontained"
        mock_siemplify.end.assert_called_once()


if __name__ == "__main__":
    unittest.main()
