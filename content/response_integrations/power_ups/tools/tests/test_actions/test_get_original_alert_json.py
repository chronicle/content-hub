# Copyright 2025 Google LLC
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

from unittest.mock import MagicMock, patch

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from ...actions import GetOriginalAlertJson
from ...core.ToolsCommon import ExecutionScope


@set_metadata(
    integration_config={},
    parameters={},
)
@patch.object(GetOriginalAlertJson, "SiemplifyAction")
def test_get_original_alert_json_alert_scope_success(
    mock_siemplify_action_class: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify
    
    mock_alert: MagicMock = MagicMock()
    mock_entity: MagicMock = MagicMock()
    mock_entity.additional_properties = {"SourceFileContent": "{\"key\": \"value\"}"}
    mock_alert.entities = [mock_entity]
    mock_siemplify.current_alert = mock_alert
    
    mock_siemplify.execution_scope = ExecutionScope.Alert
    
    GetOriginalAlertJson.main()
    
    mock_siemplify.result.add_result_json.assert_called_once_with([{"key": "value"}])
    mock_siemplify.end.assert_called_once_with(
        "See technical details", "[{\"key\": \"value\"}]")
