from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import SendPhoto
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestSendPhoto:
    CHAT_ID = "123456789"
    PHOTO_URL = "http://example.com/photo.jpg"

    @set_metadata(
        parameters={"Chat ID": CHAT_ID, "Photo URL": PHOTO_URL},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_photo_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_send_photo_response = {
            "ok": True,
            "result": {"chat_id": self.CHAT_ID, "photo_url": self.PHOTO_URL},
        }
        telegram.set_send_photo_response(expected_send_photo_response)

        SendPhoto.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/sendPhoto")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "photo": self.PHOTO_URL,
        }

        assert action_output.results.output_message == "The photo was sent successfully"
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.json_output.json_result
            == expected_send_photo_response
        )

    @set_metadata(
        parameters={"Chat ID": CHAT_ID, "Photo URL": PHOTO_URL},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_send_photo_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            SendPhoto.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/sendPhoto")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "photo": self.PHOTO_URL,
        }

        assert (
            action_output.results.output_message
            == "Could not send photo. Error: b'Simulated API failure for SendPhoto'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
