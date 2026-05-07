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

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from ...actions import AttachPlaybookToAlert
from ..common import (
    ALERTS_ALERT_SCOPE_KEY,
    ALERTS_CASE_SCOPE_KEY,
    ATTACH_PLAYBOOK_ALERT_SCOPE_CONTEXT,
    ATTACH_PLAYBOOK_CASE_SCOPE_CONTEXT,
    ATTACH_PLAYBOOK_PARAMS,
    CASE_METADATA_KEY,
    WORKFLOW_CARDS_KEY,
)
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=ATTACH_PLAYBOOK_PARAMS,
    input_context=ATTACH_PLAYBOOK_ALERT_SCOPE_CONTEXT,
)
def test_attach_playbook_to_alert_alert_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test AttachPlaybookToAlert action under Alert scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_ALERT_SCOPE_KEY])
    tools.set_workflows(load_mock_data[WORKFLOW_CARDS_KEY])

    AttachPlaybookToAlert.main()

    assert len(script_session.request_history) == 5
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=ATTACH_PLAYBOOK_PARAMS,
    input_context=ATTACH_PLAYBOOK_CASE_SCOPE_CONTEXT,
)
def test_attach_playbook_to_alert_case_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test AttachPlaybookToAlert action under Case scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])
    tools.set_workflows(load_mock_data[WORKFLOW_CARDS_KEY])

    AttachPlaybookToAlert.main()

    assert len(script_session.request_history) == 7
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
