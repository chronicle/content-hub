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

import requests

from ..actions import ContainHost as contain_host_module
from ..core.FireEyeHXManager import FireEyeHXNotFoundError
from .common import get_summary_lines, make_entity, run_action


class TestContainHost(unittest.TestCase):
    @patch.object(contain_host_module, "FireEyeHXManager")
    @patch.object(contain_host_module, "extract_action_param")
    @patch.object(contain_host_module, "extract_configuration_param")
    @patch.object(contain_host_module, "SiemplifyAction")
    def test_contain_host_by_agent_id_success(
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
            if param_name == "Approve Containment":
                return False
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        contain_host_module.main()

        mock_manager.contain_host_by_id.assert_called_once_with("test-agent-123", approve=False)
        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "test-agent-123" in json_result["operation_results"]
        assert json_result["operation_results"]["test-agent-123"]["result"] == "success"
        assert json_result["operation_results"]["test-agent-123"]["status"] == "contained"
        assert json_result["device_metadata"] == {"_id": "test-agent-123", "hostname": "TEST-HOST"}
        mock_siemplify.end.assert_called_once_with(
            "Successfully created contain host task for Agent ID: test-agent-123",
            "true",
            0,
        )

    @patch.object(contain_host_module, "FireEyeHXManager")
    @patch.object(contain_host_module, "extract_action_param")
    @patch.object(contain_host_module, "extract_configuration_param")
    @patch.object(contain_host_module, "SiemplifyAction")
    def test_contain_host_by_agent_id_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.get_host_by_agent_id.side_effect = Exception("Not found")
        mock_manager.contain_host_by_id.side_effect = Exception("API error")

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "test-agent-123"
            if param_name == "Approve Containment":
                return False
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        contain_host_module.main()

        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "test-agent-123" in json_result["operation_results"]
        assert json_result["operation_results"]["test-agent-123"]["result"] == "failure"
        assert json_result["operation_results"]["test-agent-123"]["status"] == "failed"
        mock_siemplify.end.assert_called_once_with(
            "Failed to contain host with Agent ID: test-agent-123. Error: API error",
            "false",
            2,
        )

    @patch.object(contain_host_module, "FireEyeHXManager")
    @patch.object(contain_host_module, "extract_action_param")
    @patch.object(contain_host_module, "extract_configuration_param")
    @patch.object(contain_host_module, "SiemplifyAction")
    def test_contain_host_by_entities_success(
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
            if param_name == "Approve Containment":
                return True
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        contain_host_module.main()

        mock_manager.contain_host_by_id.assert_called_once_with("agent-entity-456", approve=True)
        mock_siemplify.result.add_result_json.assert_called_once()
        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "TEST-ENDPOINT-01" in json_result["operation_results"]
        assert json_result["operation_results"]["TEST-ENDPOINT-01"]["result"] == "success"
        assert json_result["operation_results"]["TEST-ENDPOINT-01"]["status"] == "contained"
        mock_siemplify.end.assert_called_once()


class TestContainHostSummary(unittest.TestCase):
    """Tests for the failure reason and the summary line of Contain Host."""

    def test_agent_id_not_found(self) -> None:
        """Verifies ENDPOINT_NOT_FOUND in the failure entry and the summary line for an unknown agent ID."""
        error = FireEyeHXNotFoundError("Unable to contain host bad: Host not found", 404, "ENDPOINT_NOT_FOUND")

        def setup(mock_manager):
            mock_manager.contain_host_by_id.side_effect = error

        mock_siemplify = run_action(contain_host_module, {"Agent Id": "bad"}, setup)

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["operation_results"]["bad"]["error_type"] == "ENDPOINT_NOT_FOUND"
        assert json_result["operation_results"]["bad"]["reason"] == str(error)
        mock_siemplify.end.assert_called_once_with(
            f"Failed to contain host with Agent ID: bad. Error: {error}",
            "false",
            2,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "FAILURE"
        assert summary["error_type"] == "ENDPOINT_NOT_FOUND"
        assert summary["execution_state"] == "FAILED"
        assert summary["targets"] == "1"

    def test_entities_partial_success(self) -> None:
        """Verifies the error type of each failed entity and a PARTIAL_SUCCESS summary line."""
        host = MagicMock(_id="agent-1", last_poll_timestamp=1, raw_data={})
        entities = [
            make_entity("found", "HOSTNAME"),
            make_entity("missing", "HOSTNAME"),
            make_entity("10.0.0.1", "ADDRESS"),
            make_entity("user", "USERUNIQNAME"),
        ]

        def setup(mock_manager):
            mock_manager.get_hosts.side_effect = [[host], []]
            mock_manager.get_hosts_by_ip.side_effect = requests.ConnectionError("refused")

        mock_siemplify = run_action(contain_host_module, {"Agent Id": ""}, setup, entities)

        results = mock_siemplify.result.add_result_json.call_args[0][0]["operation_results"]
        assert "error_type" not in results["found"]
        assert results["missing"]["error_type"] == "ENDPOINT_NOT_FOUND"
        assert results["10.0.0.1"]["error_type"] == "CONNECTION_ERROR"
        assert mock_siemplify.end.call_args[0][1:] == ("true", 0)
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "PARTIAL_SUCCESS"
        assert summary["error_type"] == "CONNECTION_ERROR"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("3", "2", "1")

    def test_no_supported_entities(self) -> None:
        """Verify a zero-target INVALID_INPUT line with skipped=1 when only unsupported entities are passed."""
        mock_siemplify = run_action(
            contain_host_module,
            {"Agent Id": ""},
            lambda mock_manager: None,
            [make_entity("user", "USERUNIQNAME")],
        )

        mock_siemplify.end.assert_called_once_with("No tasks were created.", "false", 0)
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "INVALID_INPUT"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("0", "0", "1")

    def test_agent_id_overrides_unsupported_entities(self) -> None:
        """Verify explicit Agent Id overrides target entities and sets skipped to 0."""
        mock_siemplify = run_action(
            contain_host_module,
            {"Agent Id": "agent-1"},
            lambda mock_manager: None,
            [make_entity("user", "USERUNIQNAME")],
        )

        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["targets"], summary["failed"], summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
            "0",
        )

    def test_setup_error_preserves_targets_and_skipped(self) -> None:
        """Verify setup error marks in-scope targets failed while keeping unsupported entities skipped."""
        entities = [make_entity("host-1", "HOSTNAME"), make_entity("user", "USERUNIQNAME")]
        with (
            patch.object(contain_host_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(contain_host_module, "extract_configuration_param"),
            patch.object(contain_host_module, "extract_action_param", return_value=""),
            patch.object(contain_host_module, "FireEyeHXManager", side_effect=requests.ConnectionError("refused")),
        ):
            mock_siemplify_action.return_value.target_entities = entities
            contain_host_module.main()

        [summary] = get_summary_lines(mock_siemplify_action.return_value)
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("1", "1", "1")

        with (
            patch.object(contain_host_module, "SiemplifyAction") as mock_override_action,
            patch.object(contain_host_module, "extract_configuration_param"),
            patch.object(
                contain_host_module,
                "extract_action_param",
                side_effect=lambda siemplify, param_name, **kwargs: "agent-1" if param_name == "Agent Id" else False,
            ),
            patch.object(contain_host_module, "FireEyeHXManager", side_effect=requests.ConnectionError("refused")),
        ):
            mock_override_action.return_value.target_entities = entities
            contain_host_module.main()

        [override_summary] = get_summary_lines(mock_override_action.return_value)
        assert (override_summary["targets"], override_summary["failed"], override_summary["skipped"]) == (
            "1",
            "1",
            "0",
        )

    def test_timeout_reports_pending_targets(self) -> None:
        """Verifies that entities not processed before the deadline count as TIMEOUT failures."""
        with patch.object(contain_host_module, "unix_now", return_value=99999999999999):
            mock_siemplify = run_action(
                contain_host_module,
                {"Agent Id": ""},
                lambda mock_manager: None,
                [make_entity("host-1", "HOSTNAME")],
            )

        assert mock_siemplify.end.call_args[0][1:] == ("false", 3)
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "TIMEOUT"
        assert summary["execution_state"] == "TIMEDOUT"
        assert summary["failed"] == "1"

    def test_setup_error_skips_logout(self) -> None:
        """Verifies that a failed login does not call logout on a missing manager."""
        with (
            patch.object(contain_host_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(contain_host_module, "extract_configuration_param"),
            patch.object(contain_host_module, "extract_action_param"),
            patch.object(contain_host_module, "FireEyeHXManager", side_effect=requests.ConnectionError("refused")),
        ):
            contain_host_module.main()

        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.end.assert_called_once_with("Failed to execute action! Error is refused", "false", 2)
        mock_siemplify.LOGGER.exception.assert_called_once_with("Failed to execute action! Error is refused")
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "CONNECTION_ERROR"
        assert summary["exc_type"] == "ConnectionError"


if __name__ == "__main__":
    unittest.main()
