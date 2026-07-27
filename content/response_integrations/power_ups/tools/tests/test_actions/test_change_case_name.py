# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "_case file")
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

from ...actions import ChangeCaseName
from ..common import (
    ALERT_SCOPE_NAME,
    ALERTS_CASE_SCOPE_KEY,
    CASE_METADATA_KEY,
    CASE_SCOPE_NAME,
    CHANGE_CASE_ALERT_FIRST_ALERT_CONTEXT,
    CHANGE_CASE_ALERT_FIRST_ALERT_PARAMS,
    CHANGE_CASE_ALERT_NOT_FIRST_ALERT_CONTEXT,
    CHANGE_CASE_CASE_SCOPE_CONTEXT,
    CHANGE_CASE_CASE_SCOPE_PARAMS,
    ORIGINAL_TITLE,
)
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=CHANGE_CASE_ALERT_FIRST_ALERT_PARAMS,
    input_context=CHANGE_CASE_ALERT_FIRST_ALERT_CONTEXT,
)
def test_change_case_name_alert_scope_first_alert(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ChangeCaseName in Alert scope when current alert is the first alert."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])

    ChangeCaseName.main()

    assert len(script_session.request_history) == 3
    assert tools.case_title == ALERT_SCOPE_NAME


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=CHANGE_CASE_ALERT_FIRST_ALERT_PARAMS,
    input_context=CHANGE_CASE_ALERT_NOT_FIRST_ALERT_CONTEXT,
)
def test_change_case_name_alert_scope_not_first_alert(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ChangeCaseName in Alert scope when current alert is not the first alert."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])

    ChangeCaseName.main()

    assert len(script_session.request_history) == 2
    assert tools.case_title == ORIGINAL_TITLE


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=CHANGE_CASE_CASE_SCOPE_PARAMS,
    input_context=CHANGE_CASE_CASE_SCOPE_CONTEXT,
)
def test_change_case_name_case_scope_unconditional(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test ChangeCaseName in Case scope renames case unconditionally."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])

    ChangeCaseName.main()

    assert len(script_session.request_history) == 1
    assert tools.case_title == CASE_SCOPE_NAME
