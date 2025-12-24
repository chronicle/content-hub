from __future__ import annotations

import datetime
import unittest.mock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from sample_integration.actions import async_action_example
from sample_integration.tests.common import (
    CONFIG_PATH,
    GET_CASE_DETAILS,
    MOCK_RATES_DEFAULT,
)
from sample_integration.tests.core.product import VatComply
from sample_integration.tests.core.session import VatComplySession

CASE_ID: int = 1
TAG: str = "Async"
DEFAULT_PARAMETERS: dict[str, str] = {
    "Case IDs": f"{CASE_ID}",
    "Case Tag To Wait For": TAG,
}
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC)
    },
)
def test_async_action_example_first_run_success(
    script_session: VatComplySession,
    action_output: MockActionOutput,
    vatcomply: VatComply,
) -> None:
    # Arrange
    with unittest.mock.patch(
        "TIPCommon.base.action.Action.is_first_run",
        return_value=True,
    ):
        today: str = datetime.date.today().isoformat()
        MOCK_RATES_DEFAULT["date"]: str = today
        vatcomply.set_rates(MOCK_RATES_DEFAULT)
        vatcomply.add_case_details(CASE_ID, GET_CASE_DETAILS)
        success_output_msg = f'Action is waiting for the cases "{CASE_ID}" to have a tag {TAG}...'

        # Act
        async_action_example.main()

        # Assert
        assert len(script_session.request_history) == 1
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC)
    },
)
def test_async_action_example_second_run_success(
    script_session: VatComplySession,
    action_output: MockActionOutput,
    vatcomply: VatComply,
) -> None:
    # Arrange
    with unittest.mock.patch(
        "TIPCommon.base.action.Action.is_first_run",
        return_value=False,
    ):
        today: str = datetime.date.today().isoformat()
        MOCK_RATES_DEFAULT["date"]: str = today
        vatcomply.set_rates(MOCK_RATES_DEFAULT)
        vatcomply.add_case_details(CASE_ID, GET_CASE_DETAILS)
        vatcomply.add_tag(CASE_ID, TAG)
        success_output_msg = f'The following cases have tag "{TAG}": {CASE_ID}'

        # Act
        async_action_example.main()

        # Assert
        assert len(script_session.request_history) == 1
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.json_output.json_result == [
            {"case_id": str(CASE_ID), "tags": [TAG]}
        ]
