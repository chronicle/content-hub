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

import pytest
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import EnrichEntityFromEventField
from ..common import (
    ACTION_ALERT_SCOPE_CONTEXT,
    ACTION_ALERT_SCOPE_PARAMS,
    ACTION_CASE_SCOPE_CONTEXT,
    ACTION_CASE_SCOPE_PARAMS,
    ALERTS_ALERT_SCOPE_KEY,
    ALERTS_CASE_SCOPE_KEY,
    ALERTS_EMPTY_EVENTS_KEY,
    CASE_METADATA_KEY,
    MOCK_DATA,
    SUCCESS_OUTPUT_MESSAGE_0,
    SUCCESS_OUTPUT_MESSAGE_1,
    SUCCESS_OUTPUT_MESSAGE_2,
)
from ..core.product import EnrichmentProduct
from ..core.session import EnrichmentMockSession


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=ACTION_ALERT_SCOPE_PARAMS,
    input_context=ACTION_ALERT_SCOPE_CONTEXT,
)
def test_enrich_entity_from_event_field_alert_scope(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
) -> None:
    """Test EnrichEntityFromEventField action under Alert scope."""
    product.set_case_metadata(MOCK_DATA[CASE_METADATA_KEY])
    product.set_alerts_full_details(MOCK_DATA[ALERTS_ALERT_SCOPE_KEY])

    EnrichEntityFromEventField.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE_1
    assert action_output.results.result_value == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.execution_scope("Case")
@set_metadata(
    parameters=ACTION_CASE_SCOPE_PARAMS,
    input_context=ACTION_CASE_SCOPE_CONTEXT,
)
def test_enrich_entity_from_event_field_case_scope(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
) -> None:
    """Test EnrichEntityFromEventField action under Case scope."""
    product.set_case_metadata(MOCK_DATA[CASE_METADATA_KEY])
    product.set_alerts_full_details(MOCK_DATA[ALERTS_CASE_SCOPE_KEY])

    EnrichEntityFromEventField.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE_2
    assert action_output.results.result_value == 2
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@pytest.mark.execution_scope("Alert")
@set_metadata(
    parameters=ACTION_ALERT_SCOPE_PARAMS,
    input_context=ACTION_ALERT_SCOPE_CONTEXT,
)
def test_enrich_entity_from_event_field_empty_events(
    product: EnrichmentProduct,
    script_session: EnrichmentMockSession,
    action_output: MockActionOutput,
) -> None:
    """Test EnrichEntityFromEventField action with empty security events."""
    product.set_case_metadata(MOCK_DATA[CASE_METADATA_KEY])
    product.set_alerts_full_details(MOCK_DATA[ALERTS_EMPTY_EVENTS_KEY])

    EnrichEntityFromEventField.main()

    assert len(script_session.request_history) == 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE_0
    assert action_output.results.result_value == 0
    assert action_output.results.execution_state == ExecutionState.COMPLETED

