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

from TIPCommon.base.action import ExecutionState

from ...actions import WaitForPlaybookToComplete


@set_metadata(
    integration_config={},
    parameters={
        "Playbook Name": "MyPlaybook",
    },
)
@patch.object(WaitForPlaybookToComplete, "get_workflow_instance_card")
@patch.object(WaitForPlaybookToComplete, "SiemplifyAction")
def test_wait_for_playbook_to_complete_success(
    mock_siemplify_action_class: MagicMock,
    mock_get_workflow_instance_card: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify
    
    mock_siemplify.parameters = {"Playbook Name": "MyPlaybook"}
    
    mock_alert: MagicMock = MagicMock()
    mock_alert.identifier = "alert1"
    type(mock_siemplify).current_alert = PropertyMock(return_value=mock_alert)
    
    mock_get_workflow_instance_card.return_value = [
        {"playbookName": "MyPlaybook", "status": "COMPLETED"}
    ]
    
    WaitForPlaybookToComplete.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "Playbook MyPlaybook Finished or not found" in args[0]
