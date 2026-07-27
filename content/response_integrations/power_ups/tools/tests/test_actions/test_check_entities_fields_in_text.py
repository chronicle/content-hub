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

from typing import TYPE_CHECKING, Any

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from ...actions import CheckEntitiesFieldsInText
from ..common import (
    ALERTS_ALERT_SCOPE_KEY,
    ALERTS_CASE_SCOPE_KEY,
    CASE_METADATA_KEY,
    CHECK_ENTITIES_ALERT_SCOPE_CONTEXT,
    CHECK_ENTITIES_ALERT_SCOPE_ENTITIES,
    CHECK_ENTITIES_CASE_SCOPE_CONTEXT,
    CHECK_ENTITIES_PARAMS,
    OTHER_IP,
    TARGET_IP,
)
from ..conftest import MockEntity
from ..core.product import Tools
from ..core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=CHECK_ENTITIES_PARAMS,
    entities=CHECK_ENTITIES_ALERT_SCOPE_ENTITIES,
    input_context=CHECK_ENTITIES_ALERT_SCOPE_CONTEXT,
)
def test_check_entities_fields_in_text_alert_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test CheckEntitiesFieldsInText action under Alert scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_ALERT_SCOPE_KEY])

    CheckEntitiesFieldsInText.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert TARGET_IP in action_output.results.output_message

    assert len(script_session.request_history) == 3


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=CHECK_ENTITIES_PARAMS,
    input_context=CHECK_ENTITIES_CASE_SCOPE_CONTEXT,
)
def test_check_entities_fields_in_text_case_scope(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test CheckEntitiesFieldsInText action under Case scope."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_CASE_SCOPE_KEY])

    CheckEntitiesFieldsInText.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert TARGET_IP in action_output.results.output_message
    assert OTHER_IP not in action_output.results.output_message

    assert len(script_session.request_history) == 3


class BrokenEntity:
    """A mock entity designed to raise an exception when properties are accessed."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier

    @property
    def additional_properties(self) -> Any:
        raise RuntimeError("Simulated property retrieval failure")


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=CHECK_ENTITIES_PARAMS,
    entities=[
        MockEntity(identifier=TARGET_IP, additional_properties={"key1": "val1"}),
        BrokenEntity(identifier="192.168.1.99"),
    ],
    input_context=CHECK_ENTITIES_ALERT_SCOPE_CONTEXT,
)
def test_check_entities_fields_in_text_partial_failure(
    tools: Tools,
    script_session: ToolsSession,
    load_mock_data: SingleJson,
    action_output: MockActionOutput,
) -> None:
    """Test CheckEntitiesFieldsInText action under partial entity failure."""
    tools.set_case_metadata(load_mock_data[CASE_METADATA_KEY])
    tools.set_alerts_full_details(load_mock_data[ALERTS_ALERT_SCOPE_KEY])

    CheckEntitiesFieldsInText.main()

    from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED

    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
    assert TARGET_IP in action_output.results.output_message
    assert "Successfully processed entities" in action_output.results.output_message
    assert "192.168.1.99" in action_output.results.output_message
    assert "Failed processing entities" in action_output.results.output_message

    assert len(script_session.request_history) == 3
