from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import SendMessage
from ..common import CONFIG_PATH, TEST_BOT_TOKEN
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestSendMessage:
    MESSAGE_CONTENT = "Hello, Telegram!"
    CHAT_ID = "123456789"

    @set_metadata(
        parameters={"Message": MESSAGE_CONTENT, "Chat ID": CHAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_message_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_message_response = {
            "ok": True,
            "result": {"chat_id": self.CHAT_ID, "text": self.MESSAGE_CONTENT},
        }

        SendMessage.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path == f"/bot{TEST_BOT_TOKEN}/sendMessage"
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "text": self.MESSAGE_CONTENT,
        }

        assert (
            action_output.results.output_message == "The message was sent successfully"
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.json_output.json_result == expected_message_response
        )

    @set_metadata(
        parameters={"Message": MESSAGE_CONTENT, "Chat ID": CHAT_ID},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_message_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            SendMessage.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path == f"/bot{TEST_BOT_TOKEN}/sendMessage"
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "text": self.MESSAGE_CONTENT,
        }

        assert (
            action_output.results.output_message
            == "Could not send message. Error: b'Simulated API failure for SendMessage'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
