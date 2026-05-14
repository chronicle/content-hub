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

from unittest.mock import MagicMock, patch, PropertyMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from ...actions import LockPlaybook
from ...core.ToolsCommon import ExecutionScope


@set_metadata(
    integration_config={},
    parameters={},
)
@patch.object(LockPlaybook, "get_workflow_instance_card")
@patch.object(LockPlaybook, "SiemplifyAction")
def test_lock_playbook_success(
    mock_siemplify_action_class: MagicMock,
    mock_get_workflow_instance_card: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify
    
    mock_alert: MagicMock = MagicMock()
    mock_alert.identifier = "alert1"
    mock_alert.creation_time = 100
    type(mock_siemplify).current_alert = PropertyMock(return_value=mock_alert)
    mock_siemplify.alert_id = "alert1"
    
    mock_case: MagicMock = MagicMock()
    mock_case.alerts = [mock_alert]
    mock_siemplify.case = mock_case
    
    mock_execution_scope: MagicMock = MagicMock()
    mock_execution_scope.value = ExecutionScope.Alert.value
    mock_siemplify.execution_scope = mock_execution_scope
    
    mock_get_workflow_instance_card.return_value = {"status": "COMPLETED"}
    
    LockPlaybook.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "First alert - continuing playbook" in args[0]
