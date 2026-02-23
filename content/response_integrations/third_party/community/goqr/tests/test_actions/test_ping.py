from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from goqr.actions import ping
from goqr.tests.common import CONFIG_PATH, GENERATE_QR_CODE_RESULT
from goqr.tests.core.product import GOQR
from goqr.tests.core.session import GOQRSession


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
