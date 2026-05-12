from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import Ping
from ..common import CONFIG_PATH
from ..core.product import Abnormal
from ..core.session import AbnormalSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: AbnormalSession,
        action_output: MockActionOutput,
        abnormal: Abnormal,
    ) -> None:
        abnormal.set_threats_list_response({"threats": [], "total": 0})

        Ping.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/v1/threats")

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        script_session: AbnormalSession,
        action_output: MockActionOutput,
        abnormal: Abnormal,
    ) -> None:
        with abnormal.fail_requests():
            Ping.main()

        assert len(script_session.request_history) >= 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/v1/threats")

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect" in action_output.results.output_message
