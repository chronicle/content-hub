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

import json
import unittest
from unittest.mock import MagicMock, patch

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyUtils import unix_now

from ..actions import GetFile as get_file_module
from ..core import UtilsManager as utils_module
from ..core.FireEyeHXManager import (
    FireEyeHXManagerError,
    FireEyeHXNotFoundError,
)
from ..core.UtilsManager import TIMEOUT_MARKER_LOGGED_KEY
from .common import get_summary_lines, make_entity


class TestGetFile(unittest.TestCase):
    @patch.object(get_file_module, "FireEyeHXManager")
    @patch.object(get_file_module, "extract_action_param")
    @patch.object(get_file_module, "extract_configuration_param")
    @patch.object(get_file_module, "SiemplifyAction")
    def test_start_file_acquisition_success(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.resolve_agent_id_from_entities.return_value = "agent-xyz-123"
        mock_manager.create_file_acquisition.return_value = {"_id": 99}

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "agent-xyz-123"
            if param_name == "File Path":
                return "C:\\windows\\system32\\notepad.exe"
            if param_name == "Use API Mode":
                return False
            if param_name == "External Id":
                return "ext-alert-1"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_file_module.main(is_first_run=True)

        mock_manager.create_file_acquisition.assert_called_once_with(
            agent_id="agent-xyz-123",
            file_path="C:\\windows\\system32",
            file_name="notepad.exe",
            external_id="ext-alert-1",
            use_api_mode=False,
            comment="Acquiring file through Chronicle SOAR",
        )
        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "File acquisition 99 requested" in args[0]
        assert args[2] == 1  # EXECUTION_STATE_INPROGRESS

    @patch.object(get_file_module, "FireEyeHXManager")
    @patch.object(get_file_module, "extract_action_param")
    @patch.object(get_file_module, "extract_configuration_param")
    @patch.object(get_file_module, "SiemplifyAction")
    def test_start_file_acquisition_host_not_found(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.resolve_agent_id_from_entities.return_value = "invalid-agent"
        mock_manager.create_file_acquisition.side_effect = FireEyeHXNotFoundError(
            "HTTP Error 404: Host with the specified agent id (invalid-agent) was not found"
        )

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "invalid-agent"
            if param_name == "File Path":
                return "/tmp/malware.sh"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_file_module.main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "Host with the specified agent id (invalid-agent) was not found" in args[0]
        assert args[1] == "false"
        assert args[2] == 2  # EXECUTION_STATE_FAILED

    @patch.object(get_file_module, "FireEyeHXManager")
    @patch.object(get_file_module, "extract_action_param")
    @patch.object(get_file_module, "extract_configuration_param")
    @patch.object(get_file_module, "SiemplifyAction")
    def test_start_file_acquisition_not_supported_405(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.resolve_agent_id_from_entities.return_value = "linux-agent"
        mock_manager.create_file_acquisition.side_effect = FireEyeHXManagerError(
            "HTTP Error 405: File acquisitions are not supported by the target host"
        )

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Agent Id":
                return "linux-agent"
            if param_name == "File Path":
                return "/tmp/malware.sh"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_file_module.main(is_first_run=True)

        mock_siemplify.end.assert_called_once()
        args = mock_siemplify.end.call_args[0]
        assert "File acquisitions are not supported by the target host" in args[0]
        assert args[1] == "false"
        assert args[2] == 2

    @patch.object(get_file_module, "extract_zip_metadata")
    @patch.object(get_file_module, "FireEyeHXManager")
    @patch.object(get_file_module, "extract_action_param")
    @patch.object(get_file_module, "extract_configuration_param")
    @patch.object(get_file_module, "SiemplifyAction")
    def test_poll_file_acquisition_completed(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
        mock_extract_zip,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_extract_zip.return_value = {"md5": "abcd1234efgh"}

        mock_manager.get_file_acquisition_by_id.return_value = {
            "_id": 99,
            "state": "COMPLETE",
            "zip_file_size": 1024,
            "zip_passphrase": "secret-passphrase",
        }

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "additional_data":
                return json.dumps({
                    "acquisition_id": 99,
                    "agent_id": "agent-xyz-123",
                    "file_name": "notepad.exe",
                    "file_path": "C:\\windows\\system32",
                })
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        get_file_module.main(is_first_run=False)

        mock_manager.get_file_acquisition_by_id.assert_called_once_with(99)
        mock_manager.download_file_acquisition.assert_called_once()
        mock_siemplify.result.add_result_json.assert_called_once()
        json_res = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_res["state"] == "COMPLETE"
        assert json_res["md5"] == "abcd1234efgh"
        assert "download_path" in json_res
        assert json_res["download_path"].endswith(".zip")
        mock_siemplify.end.assert_called_once_with(
            "File 'notepad.exe' was successfully acquired from host agent-xyz-123.",
            "true",
            0,
        )


ACQUIRED_FILE_MANIFEST = {
    "audits": [
        {
            "generator": "w32rawfile-acquisition",
            "results": [{"payload": "a1b2", "type": "application/octet-stream"}],
        }
    ]
}
POLL_CONTEXT = {"acquisition_id": 99, "agent_id": "agent-1", "file_name": "a.exe", "file_path": "C:\\temp"}


class TestGetFileSummary(unittest.TestCase):
    """Tests for the failure reason and the summary line of Get File."""

    def run_action(self, is_first_run, manager_setup, **options):
        """Run the action with a mocked manager.

        Args:
            is_first_run: Whether the run is the first run.
            manager_setup: Configure the mocked manager.
            **options: agent_id, context (async state), entities, manifest, and deadline.

        Returns:
            The mocked action object.
        """
        agent_id = options.get("agent_id", "agent-1")
        params = {
            "Agent Id": agent_id,
            "File Path": "C:\\temp\\a.exe",
            "additional_data": json.dumps(options.get("context", POLL_CONTEXT)),
        }
        with (
            patch.object(get_file_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(get_file_module, "extract_configuration_param"),
            patch.object(get_file_module, "extract_action_param") as mock_extract_action,
            patch.object(get_file_module, "extract_zip_metadata", return_value=options.get("manifest", {})),
            patch.object(get_file_module, "FireEyeHXManager") as mock_manager_cls,
        ):
            mock_siemplify = mock_siemplify_action.return_value
            mock_siemplify.target_entities = options.get("entities", [])
            mock_siemplify.async_total_duration_deadline = options.get("deadline", 0)
            mock_siemplify.async_polling_interval_in_sec = 30
            mock_extract_action.side_effect = lambda siemplify, param_name, **kwargs: params.get(
                param_name, kwargs.get("default_value")
            )
            mock_manager = mock_manager_cls.return_value
            mock_manager.resolve_agent_id_from_entities.return_value = agent_id
            mock_manager.lookup_errors = []
            manager_setup(mock_manager)
            get_file_module.main(is_first_run=is_first_run)

        return mock_siemplify

    @staticmethod
    def complete(mock_manager):
        """Make the acquisition complete.

        Args:
            mock_manager: The mocked manager.
        """
        mock_manager.get_file_acquisition_by_id.return_value = {"_id": 99, "state": "COMPLETE", "zip_file_size": 10}

    def test_acquired_file(self) -> None:
        """Verifies file_acquired true and a SUCCESS summary line when the package has the file."""
        mock_siemplify = self.run_action(False, self.complete, manifest=ACQUIRED_FILE_MANIFEST)

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["file_acquired"] is True
        assert "error_type" not in json_result
        mock_siemplify.end.assert_called_once_with(
            "File 'a.exe' was successfully acquired from host agent-1.",
            "true",
            0,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "SUCCESS"
        assert summary["error_type"] == "NONE"
        assert summary["execution_state"] == "COMPLETED"

    def test_missing_file_keeps_success(self) -> None:
        """Verifies file_acquired false and FILE_NOT_FOUND while the action still completes with true."""
        manifest = {"audits": [{"generator": "w32rawfile-acquisition", "results": []}]}
        mock_siemplify = self.run_action(False, self.complete, manifest=manifest)

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert json_result["file_acquired"] is False
        assert json_result["error_type"] == "FILE_NOT_FOUND"
        mock_siemplify.end.assert_called_once_with(
            "File 'a.exe' was successfully acquired from host agent-1.",
            "true",
            0,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "FAILURE"
        assert summary["error_type"] == "FILE_NOT_FOUND"
        assert summary["execution_state"] == "COMPLETED"

    def test_has_acquired_file_shapes(self) -> None:
        """Verify has_acquired_file never raises and returns None for missing or malformed manifests."""
        cases = [
            (None, None),
            ([], None),
            ({}, None),
            ({"audits": None}, None),
            ({"audits": [None, {"generator": "file-acquisition", "results": None}]}, False),
            ({"audits": [None, {"generator": "w32rawfile-acquisition", "results": None}]}, False),
            (
                {
                    "audits": [
                        {
                            "generator": "w32rawfile-acquisition",
                            "results": [None, {"payload": "", "type": "application/octet-stream"}],
                        }
                    ]
                },
                False,
            ),
            (ACQUIRED_FILE_MANIFEST, True),
        ]
        for manifest, expected in cases:
            with self.subTest(manifest=manifest):
                assert get_file_module.has_acquired_file(manifest) is expected

    def test_empty_manifest_keeps_success(self) -> None:
        """Verify an empty manifest omits file_acquired and error_type, completes with true, and logs VENDOR_ERROR."""
        mock_siemplify = self.run_action(False, self.complete, manifest={})

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "file_acquired" not in json_result
        assert "error_type" not in json_result
        mock_siemplify.end.assert_called_once_with(
            "File 'a.exe' was successfully acquired from host agent-1.",
            "true",
            EXECUTION_STATE_COMPLETED,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "FAILURE"
        assert summary["error_type"] == "VENDOR_ERROR"
        assert summary["execution_state"] == "COMPLETED"

    def test_malformed_manifest_keeps_success(self) -> None:
        """Verify a malformed manifest does not crash, completes with true, and logs VENDOR_ERROR."""
        mock_siemplify = self.run_action(False, self.complete, manifest={"audits": None})

        json_result = mock_siemplify.result.add_result_json.call_args[0][0]
        assert "file_acquired" not in json_result
        assert "error_type" not in json_result
        mock_siemplify.end.assert_called_once_with(
            "File 'a.exe' was successfully acquired from host agent-1.",
            "true",
            EXECUTION_STATE_COMPLETED,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["outcome"] == "FAILURE"
        assert summary["error_type"] == "VENDOR_ERROR"
        assert summary["execution_state"] == "COMPLETED"

    def test_create_errors(self) -> None:
        """Verifies the error type of each create acquisition failure."""
        cases = [
            (FireEyeHXNotFoundError("host", status_code=404, error_type="ENDPOINT_NOT_FOUND"), "ENDPOINT_NOT_FOUND"),
            (FireEyeHXNotFoundError("dev", status_code=404, error_type="ENDPOINT_UNAVAILABLE"), "ENDPOINT_UNAVAILABLE"),
            (FireEyeHXManagerError("405", status_code=405, error_type="UNSUPPORTED_ENDPOINT"), "UNSUPPORTED_ENDPOINT"),
            (ValueError("boom"), "UNKNOWN_ERROR"),
        ]
        for error, expected in cases:
            with self.subTest(expected=expected):

                def setup(mock_manager, error=error):
                    mock_manager.create_file_acquisition.side_effect = error

                mock_siemplify = self.run_action(True, setup)

                assert mock_siemplify.end.call_args[0][1:] == ("false", 2)
                [summary] = get_summary_lines(mock_siemplify)
                assert summary["error_type"] == expected
                assert summary["execution_state"] == "FAILED"
                assert summary["targets"] == "1"

    def test_no_acquisition_id(self) -> None:
        """Verifies VENDOR_ERROR when the create response has no acquisition ID."""

        def setup(mock_manager):
            mock_manager.create_file_acquisition.return_value = {}

        mock_siemplify = self.run_action(True, setup)

        assert get_summary_lines(mock_siemplify)[0]["error_type"] == "VENDOR_ERROR"

    def test_no_agent_without_entities(self) -> None:
        """Verifies a zero-target INVALID_INPUT line when there is no Agent Id and no entity."""
        mock_siemplify = self.run_action(True, lambda mock_manager: None, agent_id=None)

        mock_siemplify.end.assert_called_once_with(
            "No valid agent_id was supplied or found across target entities.",
            "false",
            2,
        )
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "INVALID_INPUT"
        assert summary["targets"] == "0"

    def test_no_agent_after_failed_lookup(self) -> None:
        """Verifies that a failed host lookup request is reported instead of ENDPOINT_NOT_FOUND."""
        entity = MagicMock(identifier="host-1", entity_type="HOSTNAME")

        def setup(mock_manager):
            mock_manager.lookup_errors = [requests.ConnectionError("refused")]

        mock_siemplify = self.run_action(True, setup, agent_id=None, entities=[entity])

        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "CONNECTION_ERROR"
        assert summary["targets"] == "1"

    def test_poll_errors(self) -> None:
        """Verifies the error type of each polling failure."""
        cases = [
            ({"_id": 99, "state": "COMPLETE", "zip_file_size": 200 * 1024 * 1024}, None, "FILE_RESTRICTED"),
            ({"_id": 99, "state": "FAILED"}, None, "VENDOR_ERROR"),
            ({"_id": 99, "state": "EXPIRED"}, None, "TIMEOUT"),
            ({"_id": 99, "state": "DELETED"}, None, "CANCELLED"),
            ({"_id": 99, "state": "CANCELLED"}, None, "CANCELLED"),
            ({"_id": 99, "state": "COMPLETE"}, FireEyeHXManagerError("x", status_code=500), "VENDOR_ERROR"),
        ]
        for data, download_error, expected in cases:
            with self.subTest(expected=expected, state=data["state"]):

                def setup(mock_manager, data=data, download_error=download_error):
                    mock_manager.get_file_acquisition_by_id.return_value = data
                    mock_manager.download_file_acquisition.side_effect = download_error

                mock_siemplify = self.run_action(False, setup)

                assert mock_siemplify.end.call_args[0][1:] == ("false", 2)
                assert get_summary_lines(mock_siemplify)[0]["error_type"] == expected

    def test_status_fetch_error(self) -> None:
        """Verifies the error type when the acquisition status cannot be fetched."""

        def setup(mock_manager):
            mock_manager.get_file_acquisition_by_id.side_effect = FireEyeHXManagerError("x", status_code=401)

        mock_siemplify = self.run_action(False, setup)

        assert get_summary_lines(mock_siemplify)[0]["error_type"] == "AUTHENTICATION_FAILED"

    def test_in_progress_poll_has_no_line(self) -> None:
        """Verifies that an in-progress poll far from the deadline logs no line and keeps the old state."""

        def setup(mock_manager):
            mock_manager.get_file_acquisition_by_id.return_value = {"_id": 99, "state": "RUNNING"}

        mock_siemplify = self.run_action(False, setup, deadline=unix_now() + 3_600_000)

        assert mock_siemplify.end.call_args[0][2] == 1
        assert get_summary_lines(mock_siemplify) == []
        assert json.loads(mock_siemplify.end.call_args[0][1]) == POLL_CONTEXT

    def test_timeout_marker_once(self) -> None:
        """Verifies one IN_PROGRESS TIMEOUT marker near the deadline, with the flag saved in the state."""

        def setup(mock_manager):
            mock_manager.get_file_acquisition_by_id.return_value = {"_id": 99, "state": "ERROR"}

        first = self.run_action(False, setup, deadline=unix_now() + 10_000)
        state = json.loads(first.end.call_args[0][1])
        second = self.run_action(False, setup, deadline=unix_now() + 10_000, context=state)

        assert first.end.call_args[0][2] == 1
        assert second.end.call_args[0][2] == 1
        [marker] = get_summary_lines(first)
        assert marker["error_type"] == "TIMEOUT"
        assert marker["execution_state"] == "IN_PROGRESS"
        assert state[TIMEOUT_MARKER_LOGGED_KEY] is True
        assert get_summary_lines(second) == []

    def test_setup_error_skips_logout(self) -> None:
        """Verifies that a failed login logs the run error and does not call logout on a missing manager."""
        with (
            patch.object(get_file_module, "SiemplifyAction") as mock_siemplify_action,
            patch.object(get_file_module, "extract_configuration_param"),
            patch.object(get_file_module, "extract_action_param"),
            patch.object(get_file_module, "FireEyeHXManager", side_effect=FireEyeHXManagerError("x", status_code=401)),
        ):
            get_file_module.main(is_first_run=True)

        mock_siemplify = mock_siemplify_action.return_value
        mock_siemplify.end.assert_called_once_with("Failed to execute action! Error is x", "false", 2)
        mock_siemplify.LOGGER.exception.assert_called_once_with("Failed to execute action! Error is x")
        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "AUTHENTICATION_FAILED"
        assert summary["exc_type"] == "FireEyeHXManagerError"
        assert summary["http_status"] == "401"

    def test_summary_failure_keeps_result(self) -> None:
        """Verifies that a failing summary logger does not change the result of the action."""

        def setup(mock_manager):
            mock_manager.create_file_acquisition.return_value = {}

        with patch.object(utils_module, "build_action_result_summary", side_effect=RuntimeError("boom")):
            mock_siemplify = self.run_action(True, setup)

        mock_siemplify.end.assert_called_once_with(
            "Failed to acquire file: No acquisition ID in response data: {}",
            "false",
            2,
        )

    def test_only_unsupported_entity_reports_skipped(self) -> None:
        """Verify unsupported entities report skipped=1 when no Agent Id is provided."""
        mock_siemplify = self.run_action(
            True,
            lambda mock_manager: None,
            agent_id=None,
            entities=[make_entity("user", "USERUNIQNAME")],
        )

        [summary] = get_summary_lines(mock_siemplify)
        assert summary["error_type"] == "INVALID_INPUT"
        assert (summary["targets"], summary["failed"], summary["skipped"]) == ("0", "0", "1")

    def test_skipped_persisted_across_async_polls(self) -> None:
        """Verify skipped_count is persisted on first run and preserved across polling runs."""
        entities = [make_entity("host-1", "HOSTNAME"), make_entity("user", "USERUNIQNAME")]

        def first_setup(mock_manager):
            mock_manager.resolve_agent_id_from_entities.return_value = "agent-1"
            mock_manager.create_file_acquisition.return_value = {"_id": 99}

        def running_setup(mock_manager):
            mock_manager.get_file_acquisition_by_id.return_value = {"_id": 99, "state": "RUNNING"}

        first = self.run_action(True, first_setup, agent_id=None, entities=entities)
        first_state = json.loads(first.end.call_args[0][1])
        assert first_state["skipped_count"] == 1

        poll = self.run_action(False, running_setup, agent_id=None, context=first_state, deadline=unix_now() + 10_000)
        poll_state = json.loads(poll.end.call_args[0][1])
        [marker] = get_summary_lines(poll)
        assert marker["skipped"] == "1"

        final = self.run_action(
            False,
            self.complete,
            agent_id=None,
            context=poll_state,
            manifest=ACQUIRED_FILE_MANIFEST,
        )
        [summary] = get_summary_lines(final)
        assert (summary["outcome"], summary["targets"], summary["failed"], summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
            "1",
        )

    def test_agent_id_overrides_unsupported_entities_across_polls(self) -> None:
        """Verify Agent Id override persists skipped_count=0 even when entities exist on polls."""
        entities = [make_entity("user", "USERUNIQNAME")]

        def first_setup(mock_manager):
            mock_manager.create_file_acquisition.return_value = {"_id": 99}

        first = self.run_action(True, first_setup, agent_id="agent-1", entities=entities)
        first_state = json.loads(first.end.call_args[0][1])
        assert first_state["skipped_count"] == 0

        final = self.run_action(
            False,
            self.complete,
            agent_id=None,
            entities=entities,
            context=first_state,
            manifest=ACQUIRED_FILE_MANIFEST,
        )
        [summary] = get_summary_lines(final)
        assert (summary["outcome"], summary["targets"], summary["failed"], summary["skipped"]) == (
            "SUCCESS",
            "1",
            "0",
            "0",
        )


if __name__ == "__main__":
    unittest.main()
