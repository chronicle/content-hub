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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from ...actions import UpdateAlertScore
from ..common import (
    ALERT_1_CONTEXT,
)

if TYPE_CHECKING:
    pass


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters={"Input": "10"},
    input_context=ALERT_1_CONTEXT,
)
@patch.object(UpdateAlertScore, "SiemplifyAction")
def test_update_alert_score_alert_scope(
    mock_siemplify_action_class: MagicMock,
    action_output: MockActionOutput,
) -> None:
    """Test UpdateAlertScore under Alert scope."""
    mock_siemplify = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify

    mock_siemplify.parameters = {"Input": "10"}
    mock_siemplify.extract_action_param.return_value = "10"
    mock_siemplify.get_alert_context_property.return_value = "50"
    mock_siemplify.current_alert.alert_group_identifier = None

    mock_execution_scope = MagicMock()
    mock_execution_scope.value = 1  # Alert Scope
    mock_siemplify.execution_scope = mock_execution_scope

    UpdateAlertScore.main()

    mock_siemplify.set_alert_context_property.assert_called_once_with(
        "ALERT_SCORE", "60", alert_group_identifier=None
    )
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "The Alert Score has been updated to: 60" in args[0]
    assert args[1] == "60"


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters={"Input": "15"},
    input_context=ALERT_1_CONTEXT,
)
@patch.object(UpdateAlertScore, "SiemplifyAction")
def test_update_alert_score_case_scope(
    mock_siemplify_action_class: MagicMock,
    action_output: MockActionOutput,
) -> None:
    """Test UpdateAlertScore under Case scope."""
    mock_siemplify = MagicMock()
    mock_siemplify_action_class.return_value = mock_siemplify

    mock_siemplify.parameters = {"Input": "15"}
    mock_siemplify.extract_action_param.return_value = "15"

    mock_alert1 = MagicMock()
    mock_alert1.alert_group_identifier = "alert1"
    mock_alert1.identifier = "alert1"

    mock_alert2 = MagicMock()
    mock_alert2.alert_group_identifier = "alert2"
    mock_alert2.identifier = "alert2"

    mock_case = MagicMock()
    mock_case.alerts = [mock_alert1, mock_alert2]
    mock_case.open_alerts = mock_case.alerts
    mock_siemplify.case = mock_case

    # Mock getting context score return values sequentially for each alert
    mock_siemplify.get_alert_context_property.side_effect = ["30", "45"]

    mock_execution_scope = MagicMock()
    mock_execution_scope.value = 2  # Case Scope
    mock_siemplify.execution_scope = mock_execution_scope

    UpdateAlertScore.main()

    assert mock_siemplify.set_alert_context_property.call_count == 2
    mock_siemplify.end.assert_called_once()
    args, _ = mock_siemplify.end.call_args
    assert "successfully updated for 2 alert(s)" in args[0]
    assert args[1] == 2
