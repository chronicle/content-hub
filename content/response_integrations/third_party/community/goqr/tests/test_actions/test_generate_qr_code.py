from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from goqr.actions import generate_qr_code
from goqr.tests.common import CONFIG_PATH, GENERATE_QR_CODE_RESULT
from goqr.tests.core.product import GOQR
from goqr.tests.core.session import GOQRSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


DEFAULT_PARAMETERS: SingleJson = {
    "Content": "https://hianimes.se/",
}

FAILED_PARAMETERS: SingleJson = {
    "Content": "invalid",
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_generate_qr_code_success(
    script_session: GOQRSession,
    action_output: MockActionOutput,
    goqr: GOQR,
) -> None:
    # Arrange
    goqr.add_generated_qr(GENERATE_QR_CODE_RESULT)
    success_output_msg = "Successfully generated QR code and attached it to the case wall."

    # Act
    generate_qr_code.main()

    # Assert
    assert len(script_session.request_history) == 2
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/create-qr-code/")

    assert action_output.results.output_message == success_output_msg
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=FAILED_PARAMETERS)
def test_generate_qr_code_failure(
    script_session: GOQRSession,
    action_output: MockActionOutput,
    goqr: GOQR,
) -> None:
    # Arrange
    goqr.add_generated_qr(GENERATE_QR_CODE_RESULT)

    # Act
    generate_qr_code.main()

    # Assert
    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/create-qr-code/")

    assert "None Unable to generate QR code" in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED
