from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetChatDetails
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestGetChatDetails:
    CHAT_ID = "123456789"

    @set_metadata(
        parameters={"Chat ID": CHAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_chat_details_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_chat_details = {
            "ok": True,
            "result": {
                "id": self.CHAT_ID,
                "type": "channel",
                "title": "Test Chat",
                "invite_link": f"https://t.me/joinchat/test_invite_link_{self.CHAT_ID}",
            },
        }
        telegram.set_chat_details(expected_chat_details)

        GetChatDetails.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request

        assert request.url.path.endswith("/getChat")

        assert (
            action_output.results.output_message
            == f"The chat {self.CHAT_ID} was found successfully"
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == expected_chat_details

    @set_metadata(
        parameters={"Chat ID": CHAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_chat_details_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            GetChatDetails.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getChat")
        assert request.kwargs["params"] == {"chat_id": self.CHAT_ID}

        assert (
            action_output.results.output_message
            == f"Could not find The chat {self.CHAT_ID}. Error: b'Simulated API"
            " failure'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
