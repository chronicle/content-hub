from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetMessages
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestGetMessages:
    OFFSET_PARAM = "123"
    ALLOWED_UPDATES = "message,edited_channel_post"

    @set_metadata(
        parameters={"Offset Param": OFFSET_PARAM, "Allowed Updates": ALLOWED_UPDATES},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_messages_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_messages = {
            "ok": True,
            "result": [
                {
                    "update_id": 123456789,
                    "message": {
                        "message_id": 1,
                        "from": {
                            "id": 987654321,
                            "is_bot": False,
                            "first_name": "User",
                        },
                        "chat": {"id": 12345, "type": "private"},
                        "date": 1678886400,
                        "text": "Hello from Telegram!",
                    },
                }
            ],
        }
        telegram.set_updates_response(expected_messages)

        GetMessages.main()

        # Assert that the correct API call was made
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getUpdates")
        assert request.kwargs["params"] == {
            "offset": self.OFFSET_PARAM,
            "allowed_updates": self.ALLOWED_UPDATES,
        }

        assert (
            action_output.results.output_message
            == "The messages were pulled successfully."
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result == expected_messages

    @set_metadata(
        parameters={"Offset Param": OFFSET_PARAM, "Allowed Updates": ALLOWED_UPDATES},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_get_messages_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            GetMessages.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/getUpdates")
        assert request.kwargs["params"] == {
            "offset": self.OFFSET_PARAM,
            "allowed_updates": self.ALLOWED_UPDATES,
        }

        assert (
            action_output.results.output_message
            == "Could not get messages. Error: b'Simulated API failure for GetMessages'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
