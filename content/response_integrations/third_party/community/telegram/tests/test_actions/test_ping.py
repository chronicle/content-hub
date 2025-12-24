from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import Ping
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        telegram.set_bot_details({
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "test_bot",
                "username": "test_bot_username",
            },
        })

        Ping.main()

        # Assert that the correct API call was made
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getMe")

        assert action_output.results.output_message == "Connected successfully"
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            Ping.main()

        # Assert that the correct API call was made
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getMe")

        assert action_output.results.output_message == "The Connection failed"
        assert action_output.results.execution_state == ExecutionState.FAILED
