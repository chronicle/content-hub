from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from goqr.actions import scan_qr_code
from goqr.tests.common import CONFIG_PATH, SCAN_QR_CODE_RESULT
from goqr.tests.core.product import GOQR
from goqr.tests.core.session import GOQRSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


DEFAULT_PARAMETERS: SingleJson = {
    "QR Image Base64 Blob": (
        "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6AQMAAACyIsh+AAAABlBMVEX///8AAABVwtN+AAAACXBIWXMAAA7EAAAOx"
        "AGVKw4bAAABS0lEQVRoge2YSQ6DMAxFLbHoMXLUcFSOkUUltx6DgCLSriq+F1Fi3urjKSH6B3uwG1Fp4ihtYqrubA"
        "ASeKpe6nx/Yl7EUxcyGMAIIJJOIrULLvAiv2AGcATUWIkA/ATYftZgBPAVENmteW2he5z+9wayoSgg6n3qOABOgY1"
        "ZHJ7YbQFTUnsusyRypO3kkQngKqClz4sh6fQyxWQIYATIyIxpUDOdYj4EEMDDjqKbfSqKeHMBMAS4vHU1ySjA245z"
        "d0DU685I3lWdBHAJsDKoareMzFgbgCGARVJxZWvWPfXXAwDUR2U12zs8EwG4DHTzq5y3mN5oAJAfzWzME/Xi/su7q"
        "xyAMyBfD6K5tPUewAjA/vS3ZLhGzWQAR4AczZltBcBXgNbJqpmuUbp7jr474MnrpU81nAvvsxvAOcBudt2Ip7/CGZ"
        "MArgH/YC8kJenFGjk9QAAAAABJRU5ErkJggg==",
    )
}

FAILED_PARAMETERS: SingleJson = {
    "QR Image Base64 Blob": "invalid",
}


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_scan_qr_code_success(
    script_session: GOQRSession,
    action_output: MockActionOutput,
    goqr: GOQR,
) -> None:
    # Arrange
    goqr.add_scanned_qr(SCAN_QR_CODE_RESULT)
    success_output_msg = "Successfully decoded QR code from provided image content."

    # Act
    scan_qr_code.main()
    # Assert
    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/read-qr-code/")

    assert action_output.results.output_message == success_output_msg
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=FAILED_PARAMETERS)
def test_scan_qr_code_failure(
    script_session: GOQRSession,
    action_output: MockActionOutput,
    goqr: GOQR,
) -> None:
    # Arrange
    goqr.add_scanned_qr(SCAN_QR_CODE_RESULT)

    # Act
    scan_qr_code.main()
    # Assert
    assert len(script_session.request_history) == 0
    assert "Incorrect padding" in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED
