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
from ..core.FireEyeHXManager import FireEyeHXManagerError
from .common import get_summary_lines, make_entity, run_action


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


class TestCancelHostContainSummary(unittest.TestCase):
    """Tests for the failure reason and the summary line of Cancel Host Contain."""

    def test_agent_id_permission_denied(self) -> None:
        """Verifies PERMISSION_DENIED in the failure entry and the summary line."""
        error = FireEyeHXManagerError("Unable to cancel containment for host a: Forbidden", 403)

        def setup(mock_manager):
            mock_manager.cancel_containment_by_id.side_effect = error

        mock_siemplify = run_action(cancel_host_module, {"Agent Id": "a"}, setup)

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["operation_results"]["a"]["error_type"] == "PERMISSION_DENIED"
        mock_siemplify.end.assert_called_once_with(
            f"Failed to cancel contain host with Agent ID: a. Error: {error}",
            "false",
            2,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "PERMISSION_DENIED"
        assert summary["exc_type"] == "NONE"

    def test_entity_host_not_found(self) -> None:
        """Verifies ENDPOINT_NOT_FOUND for an entity without a matching host."""

        def setup(mock_manager):
            mock_manager.get_hosts.return_value = []

        mock_siemplify = run_action(cancel_host_module, {"Agent Id": ""}, setup, [make_entity("h", "HOSTNAME")])

        results = mock_siemplify.result.add_result_json.call_args[0][0]["operation_results"]
        assert results["h"]["error_type"] == "ENDPOINT_NOT_FOUND"
        assert mock_siemplify.end.call_args[0][1:] == ("false", 0)
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "FAILURE"
        assert summary["error_type"] == "ENDPOINT_NOT_FOUND"
        assert summary["execution_state"] == "COMPLETED"

    def test_success_line(self) -> None:
        """Verifies a SUCCESS summary line for a cancelled containment."""
        mock_siemplify = run_action(cancel_host_module, {"Agent Id": "a"}, lambda mock_manager: None)

        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"], summary["targets"]) == ("SUCCESS", "NONE", "1")

    def test_setup_error_skips_logout(self) -> None:
        """Verifies that a failed login does not call logout on a missing manager."""
        with (
            patch.object(cancel_host_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(cancel_host_module, "extract_configuration_param"),
            patch.object(cancel_host_module, "extract_action_param"),
            patch.object(cancel_host_module, "FireEyeHXManager", side_effect=FireEyeHXManagerError("x", 401)),
        ):
            cancel_host_module.main()

        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.LOGGER.exception.assert_called_once_with("Failed to execute action! Error is x")
        assert get_summary_lines(mock_siemplify)[0]["error_type"] == "AUTHENTICATION_FAILED"

    def test_only_unsupported_entity_reports_skipped(self) -> None:
        """Verify unsupported entities report skipped=1 when no Agent Id is provided."""
        mock_siemplify = run_action(
            cancel_host_module,
            {"Agent Id": ""},
            lambda mock_manager: None,
            [make_entity("user", "USERUNIQNAME")],
        )

        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "INVALID_INPUT"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("0", "0", "1")

    def test_unsupported_entity_skipped_vs_agent_id_override(self) -> None:
        """Verify unsupported entities increment skipped unless Agent Id overrides target entities."""
        host = MagicMock(_id="agent-1", last_poll_timestamp=1, raw_data={})
        entities = [make_entity("host-1", "HOSTNAME"), make_entity("user", "USERUNIQNAME")]

        def setup(mock_manager):
            mock_manager.get_hosts.return_value = [host]

        entity_run = run_action(cancel_host_module, {"Agent Id": ""}, setup, entities)
        override_run = run_action(cancel_host_module, {"Agent Id": "a"}, lambda mock_manager: None, entities)

        [entity_summary] = get_summary_lines(entity_run)
        [override_summary] = get_summary_lines(override_run)
        assert (entity_summary["outcome"], entity_summary["targets"], entity_summary["skipped"]) == (
            "SUCCESS",
            "1",
            "1",
        )
        assert (override_summary["outcome"], override_summary["targets"], override_summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
        )

    def test_setup_error_preserves_targets_and_skipped(self) -> None:
        """Verify setup error marks supported entities failed and keeps unsupported entities skipped."""
        entities = [make_entity("host-1", "HOSTNAME"), make_entity("user", "USERUNIQNAME")]
        with (
            patch.object(cancel_host_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(cancel_host_module, "extract_configuration_param"),
            patch.object(cancel_host_module, "extract_action_param", return_value=""),
            patch.object(cancel_host_module, "FireEyeHXManager", side_effect=FireEyeHXManagerError("x", 401)),
        ):
            mock_siemplify_action.return_value.target_entities = entities
            cancel_host_module.main()

        [summary] = get_summary_lines(mock_siemplify_action.return_value)
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("1", "1", "1")


if __name__ == "__main__":
    unittest.main()
