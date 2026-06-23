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

from integration_testing.set_meta import set_metadata

from ...actions import FindFirstAlert


@set_metadata(
    integration_config={},
    parameters={},
)
def test_find_first_alert_alert_scope_success(
    mocker,
) -> None:
    mock_siemplify = mocker.MagicMock()
    mocker.patch.object(FindFirstAlert, "SiemplifyAction", return_value=mock_siemplify)
    
    mock_case = mocker.MagicMock()
    mock_alert1 = mocker.MagicMock()
    mock_alert1.identifier = "alert1"
    mock_alert1.creation_time = 100
    
    mock_alert2 = mocker.MagicMock()
    mock_alert2.identifier = "alert2"
    mock_alert2.creation_time = 200
    
    mock_case.alerts = [mock_alert2, mock_alert1]
    mock_case.open_alerts = mock_case.alerts
    
    mock_siemplify.case = mock_case
    mock_siemplify.current_alert = mock_alert1
    
    mock_execution_scope = mocker.MagicMock()
    mock_execution_scope.value = 1  # ExecutionScope.Alert.value
    mock_siemplify.execution_scope = mock_execution_scope
    
    FindFirstAlert.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "This is the first alert." in args[0]
    assert args[1] == "alert1"


@set_metadata(
    integration_config={},
    parameters={},
)
def test_find_first_alert_case_scope_success(
    mocker,
) -> None:
    mock_siemplify = mocker.MagicMock()
    mocker.patch.object(FindFirstAlert, "SiemplifyAction", return_value=mock_siemplify)
    
    mock_case = mocker.MagicMock()
    mock_alert1 = mocker.MagicMock()
    mock_alert1.identifier = "alert1"
    mock_alert1.creation_time = 100
    
    mock_alert2 = mocker.MagicMock()
    mock_alert2.identifier = "alert2"
    mock_alert2.creation_time = 200
    
    mock_case.alerts = [mock_alert2, mock_alert1]
    mock_case.open_alerts = mock_case.alerts
    
    mock_siemplify.case = mock_case
    mock_siemplify.current_alert = mock_alert1
    
    mock_execution_scope = mocker.MagicMock()
    mock_execution_scope.value = 2  # ExecutionScope.Case.value
    mock_siemplify.execution_scope = mock_execution_scope
    
    FindFirstAlert.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "First alert of the case is: alert1" in args[0]
    assert args[1] == "alert1"


@set_metadata(
    integration_config={},
    parameters={},
)
def test_find_first_alert_empty_alerts(
    mocker,
) -> None:
    mock_siemplify = mocker.MagicMock()
    mocker.patch.object(FindFirstAlert, "SiemplifyAction", return_value=mock_siemplify)
    
    mock_case = mocker.MagicMock()
    mock_case.alerts = []
    mock_case.open_alerts = []
    
    mock_siemplify.case = mock_case
    
    mock_execution_scope = mocker.MagicMock()
    mock_execution_scope.value = 2  # ExecutionScope.Case.value
    mock_siemplify.execution_scope = mock_execution_scope
    
    FindFirstAlert.main()
    
    mock_siemplify.end.assert_called_once_with("No alerts found in the case.", "false")


@set_metadata(
    integration_config={},
    parameters={},
)
def test_find_first_alert_empty_open_alerts_fallback(
    mocker,
) -> None:
    mock_siemplify = mocker.MagicMock()
    mocker.patch.object(FindFirstAlert, "SiemplifyAction", return_value=mock_siemplify)
    
    mock_case = mocker.MagicMock()
    mock_alert1 = mocker.MagicMock()
    mock_alert1.identifier = "alert1"
    mock_alert1.creation_time = 100
    
    mock_alert2 = mocker.MagicMock()
    mock_alert2.identifier = "alert2"
    mock_alert2.creation_time = 200
    
    mock_case.alerts = [mock_alert2, mock_alert1]
    mock_case.open_alerts = []
    
    mock_siemplify.case = mock_case
    mock_siemplify.current_alert = mock_alert1
    
    mock_execution_scope = mocker.MagicMock()
    mock_execution_scope.value = 2  # ExecutionScope.Case.value
    mock_siemplify.execution_scope = mock_execution_scope
    
    FindFirstAlert.main()
    
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "First alert of the case is: alert1" in args[0]
    assert args[1] == "alert1"
