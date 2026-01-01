from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetBotDetails
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestGetBotDetails:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_get_bot_details_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_bot_details = {
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "test_bot",
                "username": "test_bot_username",
            },
        }
        telegram.set_bot_details(expected_bot_details)

        GetBotDetails.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getMe")

        assert action_output.results.output_message == "The Bot was found successfully"
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == expected_bot_details

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_get_bot_details_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            GetBotDetails.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getMe")

        assert (
            action_output.results.output_message
            == "The Bot details could not be fetched. Error: b'Simulated API failure"
            " for GetBotDetails'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
