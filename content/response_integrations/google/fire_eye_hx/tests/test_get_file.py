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
from unittest.mock import patch

from ..actions import GetFile as get_file_module
from ..core.FireEyeHXManager import (
    FireEyeHXManagerError,
    FireEyeHXNotFoundError,
)


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


if __name__ == "__main__":
    unittest.main()
