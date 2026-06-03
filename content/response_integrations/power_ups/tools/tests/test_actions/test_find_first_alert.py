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

from ...actions import FindFirstAlert


@set_metadata(
    integration_config={},
    parameters={},
)
@patch.object(FindFirstAlert, "SiemplifyAction")
def test_find_first_alert_success(
    mock_siemplify_action_class: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify
    
    mock_case: MagicMock = MagicMock()
    mock_alert1: MagicMock = MagicMock()
    mock_alert1.identifier = "alert1"
    mock_alert1.creation_time = 100
    
    mock_alert2: MagicMock = MagicMock()
    mock_alert2.identifier = "alert2"
    mock_alert2.creation_time = 200
    
    mock_case.alerts = [mock_alert2, mock_alert1]
    mock_case.open_alerts = mock_case.alerts
    
    mock_siemplify.case = mock_case
    mock_siemplify.current_alert = mock_alert1
    
    mock_execution_scope: MagicMock = MagicMock()
    mock_execution_scope.value = "Alert"
    mock_siemplify.execution_scope = mock_execution_scope
    
    FindFirstAlert.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "First alert of the case is: alert1" in args[0]
    assert args[1] == "alert1"
