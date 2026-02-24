from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

from goqr.actions import ping
from goqr.tests.common import CONFIG, CONFIG_PATH, GENERATE_QR_CODE_RESULT
from goqr.tests.core.product import GOQR
from goqr.tests.core.session import GOQRSession

FAILED_CONFIG: SingleJson = CONFIG.copy()
FAILED_CONFIG["API Root"] = "http://invalid-url.com"


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: GOQRSession,
        action_output: MockActionOutput,
        goqr: GOQR,
    ) -> None:
        goqr.add_generated_qr(GENERATE_QR_CODE_RESULT)
        success_output_msg = "Successfully connected to the QR Server API."
        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/create-qr-code/")

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config=FAILED_CONFIG)
    def test_ping_failed(
        self,
        script_session: GOQRSession,
        action_output: MockActionOutput,
        goqr: GOQR,
    ) -> None:
        goqr.add_generated_qr(GENERATE_QR_CODE_RESULT)
        failed_output_message = (
            "Failed to connect to the QR Server API. Please check the API Root.\nReason: Failed"
            " to connect to the API.: 422 Client Error: None for url: None Invalid QR Code"
        )

        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/create-qr-code/")
        assert action_output.results.output_message == failed_output_message
        assert action_output.results.execution_state == ExecutionState.FAILED
