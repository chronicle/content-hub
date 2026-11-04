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
from ..core.FireEyeHXManager import FireEyeHXManagerError, FireEyeHXNotFoundError
from .common import get_summary_lines, make_entity, run_action


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


class TestCheckContainmentStatusSummary(unittest.TestCase):
    """Tests for the failure reason and the summary line of Check Containment Status."""

    def test_status_error(self) -> None:
        """Verifies the error type in the failure entry and the summary line."""
        error = FireEyeHXNotFoundError("Unable to get containment status for host a: x", 404, "ENDPOINT_NOT_FOUND")

        def setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = "a"
            mock_manager.get_host_by_agent_id.side_effect = error
            mock_manager.get_containment_status.side_effect = error

        mock_siemplify = run_action(check_status_module, {"Agent Id": "a"}, setup)

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["operation_results"]["a"]["error_type"] == "ENDPOINT_NOT_FOUND"
        mock_siemplify.end.assert_called_once_with(
            f"Failed to get containment status for Agent ID: a. Error: {error}",
            "false",
            2,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "ENDPOINT_NOT_FOUND"
        assert summary["targets"] == "1"

    def test_success_line(self) -> None:
        """Verifies a SUCCESS summary line for a status lookup."""

        def setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = "a"
            mock_manager.get_host_by_agent_id.return_value = MagicMock(containment_state="contained", raw_data={})

        mock_siemplify = run_action(check_status_module, {"Agent Id": "a"}, setup)

        assert mock_siemplify.end.call_args[0][1:] == ("contained", 0)
        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["outcome"], summary["error_type"], summary["targets"]) == ("SUCCESS", "NONE", "1")

    def test_agent_not_found(self) -> None:
        """Verifies ENDPOINT_NOT_FOUND when no agent matches the entities."""

        def setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = None

        mock_siemplify = run_action(check_status_module, {}, setup, [make_entity("10.0.0.1", "ADDRESS")])

        mock_siemplify.end.assert_called_once_with(
            "No Agent ID was provided or could be resolved from entities.",
            "false",
            2,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "ENDPOINT_NOT_FOUND"
        assert summary["targets"] == "1"

    def test_no_input(self) -> None:
        """Verifies a zero-target INVALID_INPUT line when there is no Agent Id and no entity."""

        def setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = None

        mock_siemplify = run_action(check_status_module, {}, setup)

        [summary] = get_summary_lines(mock_siemplify)
        assert (summary["error_type"], summary["targets"]) == ("INVALID_INPUT", "0")

    def test_setup_error_skips_logout(self) -> None:
        """Verifies that a failed login does not call logout on a missing manager."""
        with (
            patch.object(check_status_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(check_status_module, "extract_configuration_param"),
            patch.object(check_status_module, "extract_action_param"),
            patch.object(check_status_module, "FireEyeHXManager", side_effect=FireEyeHXManagerError("x", 403)),
        ):
            check_status_module.main()

        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.LOGGER.exception.assert_called_once_with("Failed to execute action! Error is x")
        assert get_summary_lines(mock_siemplify)[0]["error_type"] == "PERMISSION_DENIED"

    def test_only_unsupported_entity_reports_skipped(self) -> None:
        """Verify unsupported entities report skipped=1 when no Agent Id is provided."""

        def setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = None

        mock_siemplify = run_action(check_status_module, {}, setup, [make_entity("user", "USERUNIQNAME")])

        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "INVALID_INPUT"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("0", "0", "1")

    def test_unsupported_entity_skipped_vs_agent_id_override(self) -> None:
        """Verify unsupported entities increment skipped unless Agent Id overrides target entities."""
        entities = [make_entity("10.0.0.1", "ADDRESS"), make_entity("user", "USERUNIQNAME")]

        def resolved_setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = "a"
            mock_manager.get_host_by_agent_id.return_value = MagicMock(containment_state="contained", raw_data={})

        def missing_setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = None

        entity_ok = run_action(check_status_module, {"Agent Id": ""}, resolved_setup, entities)
        entity_missing = run_action(check_status_module, {"Agent Id": ""}, missing_setup, entities)
        override_ok = run_action(check_status_module, {"Agent Id": "a"}, resolved_setup, entities)

        [ok_summary] = get_summary_lines(entity_ok)
        [missing_summary] = get_summary_lines(entity_missing)
        [override_summary] = get_summary_lines(override_ok)
        assert (ok_summary["outcome"], ok_summary["targets"], ok_summary["failed"], ok_summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
            "1",
        )
        assert (
            missing_summary["error_type"],
            missing_summary["targets"],
            missing_summary["failed"],
            missing_summary["skipped"],
        ) == ("ENDPOINT_NOT_FOUND", "1", "1", "1")
        assert (override_summary["outcome"], override_summary["targets"], override_summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
        )


if __name__ == "__main__":
    unittest.main()
