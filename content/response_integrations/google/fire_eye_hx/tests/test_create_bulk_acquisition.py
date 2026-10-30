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

from base64 import b64decode
import unittest
from unittest.mock import patch

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)

from ..actions import CreateBulkAcquisition as create_module


class TestCreateBulkAcquisition(unittest.TestCase):
    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_host_set_success(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.get_host_set_id_by_name.return_value = 9
        mock_manager.create_bulk_acquisition.return_value = {
            "_id": 101,
            "state": "RUNNING",
            "comment": "Created by Google SecOps",
        }

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return '<script><commands><command type="test"/></commands></script>'
            if param_name == "Host Set Name":
                return "all_hosts"
            if param_name == "Host Set ID":
                return ""
            if param_name == "Agent IDs":
                return ""
            if param_name == "Comment":
                return "Created by Google SecOps"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_called_once()
        call_kwargs = mock_manager.create_bulk_acquisition.call_args[1]
        assert call_kwargs["host_set_id"] == 9
        assert call_kwargs["agent_ids"] is None
        assert call_kwargs["comment"] == "Created by Google SecOps"
        mock_siemplify.result.add_result_json.assert_called_once_with({
            "_id": 101,
            "state": "RUNNING",
            "comment": "Created by Google SecOps",
        })
        mock_siemplify.end.assert_called_once_with(
            "Successfully created bulk acquisition 101. State: RUNNING",
            "101",
            EXECUTION_STATE_COMPLETED,
        )

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_agent_ids_success(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        mock_manager.create_bulk_acquisition.return_value = {
            "_id": 102,
            "state": "QUEUED",
        }

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "<script><commands/></script>"
            if param_name == "Agent IDs":
                return "agent-1, agent-2"
            if param_name == "Host Set Name":
                return ""
            if param_name == "Host Set ID":
                return ""
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_called_once()
        call_kwargs = mock_manager.create_bulk_acquisition.call_args[1]
        assert call_kwargs["agent_ids"] == ["agent-1", "agent-2"]
        mock_siemplify.end.assert_called_once_with(
            "Successfully created bulk acquisition 102. State: QUEUED",
            "102",
            EXECUTION_STATE_COMPLETED,
        )

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_agent_ids_whitespace_only_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "<script><commands/></script>"
            if param_name == "Agent IDs":
                return " , "
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Agent IDs must contain at least one agent ID" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_no_target_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "<script><commands/></script>"
            if param_name == "Agent IDs":
                return ""
            if param_name == "Host Set Name":
                return ""
            if param_name == "Host Set ID":
                return ""
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Provide Agent IDs, Host Set ID or Host Set Name" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_invalid_timeframe_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return '<script time="__INTERVAL_START__"><commands/></script>'
            if param_name == "Timeframe Start":
                return "yesterday_bad_date"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Timeframe Start must be a valid ISO timestamp" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_timeframe_stop_invalid_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return '<script time="__INTERVAL_STOP__"><commands/></script>'
            if param_name == "Timeframe Stop":
                return "invalid_stop_date"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Timeframe Stop must be a valid ISO timestamp" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_date_macro_substitution(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.create_bulk_acquisition.return_value = {"_id": 103, "state": "RUNNING"}

        raw_script = '<script time_start="__INTERVAL_START__" time_stop="__INTERVAL_STOP__"><commands/></script>'

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return raw_script
            if param_name == "Timeframe Start":
                return "2026-10-25T00:00:00"
            if param_name == "Timeframe Stop":
                return "2026-10-25T23:59:59"
            if param_name == "Host Set Name":
                return "all_hosts"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        call_kwargs = mock_manager.create_bulk_acquisition.call_args[1]
        decoded_script = b64decode(call_kwargs["script_b64"]).decode("utf-8")
        assert 'time_start="2026-10-25T00:00:00"' in decoded_script
        assert 'time_stop="2026-10-25T23:59:59"' in decoded_script

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_invalid_xml_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "<script><unclosed_tag></script>"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "invalid XML" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_python_wrapper_cleanup(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.create_bulk_acquisition.return_value = {"_id": 104, "state": "RUNNING"}

        wrapped_script = (
            '# Some legacy python comment\nSCRIPT_XML = r"""<?xml version="1.0"?><script><commands/></script>"""\n'
        )

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return wrapped_script
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        call_kwargs = mock_manager.create_bulk_acquisition.call_args[1]
        decoded = b64decode(call_kwargs["script_b64"]).decode("utf-8")
        assert decoded == '<?xml version="1.0"?><script><commands/></script>'
        mock_siemplify.end.assert_called_once_with(
            "Successfully created bulk acquisition 104. State: RUNNING",
            "104",
            EXECUTION_STATE_COMPLETED,
        )

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_unbound_prefix_namespace_injection(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.create_bulk_acquisition.return_value = {"_id": 105, "state": "RUNNING"}

        unbound_prefix_script = (
            '<script><commands><command xsi:type="ExecuteModuleCommand">'
            '<module name="test"/></command></commands></script>'
        )

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return unbound_prefix_script
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        call_kwargs = mock_manager.create_bulk_acquisition.call_args[1]
        decoded = b64decode(call_kwargs["script_b64"]).decode("utf-8")
        assert 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' in decoded
        assert 'xmlns:xsd="http://www.w3.org/2001/XMLSchema"' in decoded
        mock_siemplify.end.assert_called_once_with(
            "Successfully created bulk acquisition 105. State: RUNNING",
            "105",
            EXECUTION_STATE_COMPLETED,
        )

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_empty_script_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "   "
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_not_called()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Script Content must not be empty" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED

    @patch.object(create_module, "FireEyeHXManager")
    @patch.object(create_module, "extract_action_param")
    @patch.object(create_module, "extract_configuration_param")
    @patch.object(create_module, "SiemplifyAction")
    def test_create_bulk_acquisition_missing_id_in_response_failure(
        self,
        mock_siemplify_action,
        mock_extract_config,
        mock_extract_action,
        mock_manager_cls,
    ) -> None:
        mock_siemplify = mock_siemplify_action.return_value
        mock_manager = mock_manager_cls.return_value
        mock_manager.create_bulk_acquisition.return_value = {"state": "QUEUED"}

        def extract_action_param_side_effect(siemplify, param_name, **kwargs):
            if param_name == "Script Content":
                return "<script><commands/></script>"
            if param_name == "Agent IDs":
                return "agent-1"
            return kwargs.get("default_value")

        mock_extract_action.side_effect = extract_action_param_side_effect

        create_module.main()

        mock_manager.create_bulk_acquisition.assert_called_once()
        mock_siemplify.end.assert_called_once()
        end_call = mock_siemplify.end.call_args[0]
        assert "Response missing '_id'" in end_call[0]
        assert end_call[1] == "false"
        assert end_call[2] == EXECUTION_STATE_FAILED


if __name__ == "__main__":
    unittest.main()
