from __future__ import annotations

import pytest
from TIPCommon.base.action import ExecutionState

from protectwise.actions import GetPcap
from protectwise.tests.common import (
    CONFIG,
    EMPTY_MESSAGE,
    EVENT_NAME,
    EVENTS_RESPONSE,
    SUCCESS_MESSAGE_PREFIX,
    SUCCESS_RESULT_VALUE,
)
from protectwise.tests.core.product import ProtectwiseProduct
from protectwise.tests.core.session import ProtectwiseSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ALERT_SUCCESS_MESSAGE = (
    "Successfully downloaded pcap for events in the case timeframe: \n"
    f"{EVENT_NAME}"
)

CASE_SUCCESS_MESSAGE = (
    "Successfully downloaded pcap for events in the case timeframe "
    "for all alert(s) in case None: \n"
    f"{EVENT_NAME}"
)


@pytest.mark.execution_scope("Alert")
@set_metadata(
    integration_config=CONFIG,
)
def test_get_pcap_alert_scope_success(
    protectwise_product: ProtectwiseProduct,
    script_session: ProtectwiseSession,
    action_output: MockActionOutput,
) -> None:
    """Test successful retrieval of PCAP streams under Alert scope."""
    assert protectwise_product.get_events() == EVENTS_RESPONSE

    GetPcap.main()

    assert len(script_session.request_history) == 6
    assert action_output.results.result_value == SUCCESS_RESULT_VALUE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.output_message == ALERT_SUCCESS_MESSAGE


@pytest.mark.execution_scope("Case")
@set_metadata(
    integration_config=CONFIG,
)
def test_get_pcap_case_scope_success(
    protectwise_product: ProtectwiseProduct,
    script_session: ProtectwiseSession,
    action_output: MockActionOutput,
) -> None:
    """Test successful retrieval of PCAP streams under Case scope."""
    assert protectwise_product.get_events() == EVENTS_RESPONSE

    GetPcap.main()

    assert len(script_session.request_history) == 6
    assert action_output.results.result_value == SUCCESS_RESULT_VALUE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.output_message == CASE_SUCCESS_MESSAGE


@pytest.mark.execution_scope("Alert")
@set_metadata(
    integration_config=CONFIG,
)
def test_get_pcap_empty_results(
    protectwise_product: ProtectwiseProduct,
    script_session: ProtectwiseSession,
    action_output: MockActionOutput,
) -> None:
    """Test execution outcome when no matching events or PCAPs exist."""
    protectwise_product.should_return_empty_events = True

    GetPcap.main()

    assert len(script_session.request_history) == 4
    assert action_output.results.result_value == SUCCESS_RESULT_VALUE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.output_message == EMPTY_MESSAGE
