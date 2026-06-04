# Copyright 2026 Google LLC
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

from misp.actions import AddAttribute
from misp.tests.common import (
    CONFIG,
    DEFAULT_PARAMETERS,
    EVENT_ID,
    FAILED_OUTPUT_MESSAGE,
    FAILED_PARAMETERS,
    GET_EVENT,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
    INTEGRATION_NAME,
    SUCCESS_OUTPUT_MESSAGE,
)
from misp.tests.core.product import MISPProduct
from misp.tests.core.session import MISPSession


@pytest.mark.execution_scope("Alert")
@set_metadata(
    integration_config=CONFIG,
    parameters=DEFAULT_PARAMETERS,
    entities=[HOSTNAME_ENTITY],
)
def test_add_attribute_alert_scope_success(
    misp_product: MISPProduct,
    script_session: MISPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful execution of the AddAttribute action under Alert scope."""
    misp_product.cleanup_events()
    misp_product.add_event(EVENT_ID, GET_EVENT)

    AddAttribute.main()

    assert len(script_session.request_history) >= 4
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@pytest.mark.execution_scope("Case")
@set_metadata(
    integration_config=CONFIG,
    parameters=DEFAULT_PARAMETERS,
    entities=[HOSTNAME_ENTITY],
)
def test_add_attribute_case_scope_success(
    misp_product: MISPProduct,
    script_session: MISPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful execution of the AddAttribute action under Case scope."""
    misp_product.cleanup_events()
    misp_product.add_event(EVENT_ID, GET_EVENT)

    AddAttribute.main()

    assert len(script_session.request_history) >= 4
    expected_message = (
        "Successfully added the following attributes based on "
        "entities to the event with "
        f"ID {EVENT_ID} in {INTEGRATION_NAME} for all "
        "alert(s) in case None: \n"
        f" {HOSTNAME_ENTITY_ID} \n"
    )
    assert action_output.results.output_message == expected_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@pytest.mark.execution_scope("Alert")
@set_metadata(
    integration_config=CONFIG,
    parameters=FAILED_PARAMETERS,
    entities=[HOSTNAME_ENTITY],
)
def test_add_attribute_action_not_found_failure(
    misp_product: MISPProduct,
    script_session: MISPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for failure execution of the AddAttribute action when event is not found."""
    misp_product.cleanup_events()

    AddAttribute.main()

    assert len(script_session.request_history) >= 2
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None
