from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sample_integration.actions import simple_action_example
from sample_integration.tests.common import CONFIG_PATH, MOCK_RATES_DEFAULT
from sample_integration.tests.core.product import VatComply
from sample_integration.tests.core.session import VatComplySession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


DEFAULT_PARAMETERS: SingleJson = {
    "Currencies String": "EUR",
    "Currencies DDL": "Select One",
    "Time Frame": "Today",
    "Return JSON Result": True,
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_sample_action_example_success(
    script_session: VatComplySession,
    action_output: MockActionOutput,
    vatcomply: VatComply,
) -> None:
    # Arrange
    today: str = datetime.date.today().isoformat()
    MOCK_RATES_DEFAULT["date"]: str = today
    vatcomply.set_rates(MOCK_RATES_DEFAULT)
    success_output_msg = (
        "Successfully returned information about the following currencies from "
        f"{today} to {today} :\nEUR"
    )

    # Act
    simple_action_example.main()

    # Assert
    assert len(script_session.request_history) == 2
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/rates")

    assert action_output.results.output_message == success_output_msg
    assert action_output.results.execution_state == ExecutionState.COMPLETED
