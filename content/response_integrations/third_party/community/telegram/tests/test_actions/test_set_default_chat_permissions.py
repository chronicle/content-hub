from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import SetDefaultChatPermissions
from ..common import CONFIG_PATH
from ..core.product import Telegram
from ..core.session import TelegramSession


class TestSetDefaultChatPermissions:
    CHAT_ID = "123456789"
    CAN_SEND_POLLS = "True"
    CAN_PIN_MESSAGES = "False"
    CAN_INVITE_USERS = "True"
    CAN_EDIT_INFO = "False"
    CAN_SEND_MESSAGES = "True"

    @set_metadata(
        parameters={
            "Chat ID": CHAT_ID,
            "Can Send Polls": CAN_SEND_POLLS,
            "Can Pin Messages": CAN_PIN_MESSAGES,
            "Can Invite Users": CAN_INVITE_USERS,
            "Can Edit Info": CAN_EDIT_INFO,
            "Can Send Messages": CAN_SEND_MESSAGES,
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_set_default_chat_permissions_success(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        expected_set_default_chat_permissions_response = {
            "ok": True,
            "result": {
                "chat_id": self.CHAT_ID,
                "permissions": {
                    "can_send_polls": self.CAN_SEND_POLLS,
                    "can_pin_messages": self.CAN_PIN_MESSAGES,
                    "can_invite_users": self.CAN_INVITE_USERS,
                    "can_change_info": self.CAN_EDIT_INFO,
                    "can_post_messages": self.CAN_SEND_MESSAGES,
                },
            },
        }
        telegram.set_set_default_chat_permissions_response(
            expected_set_default_chat_permissions_response
        )

        SetDefaultChatPermissions.main()

        # Assert that the correct API call was made
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/setChatPermissions")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "can_send_polls": self.CAN_SEND_POLLS,
            "can_pin_messages": self.CAN_PIN_MESSAGES,
            "can_invite_users": self.CAN_INVITE_USERS,
            "can_change_info": self.CAN_EDIT_INFO,
            "can_send_messages": self.CAN_SEND_MESSAGES,
        }

        assert (
            action_output.results.output_message
            == f"The permissions of the chat {self.CHAT_ID} were changed successfully"
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.json_output.json_result
            == expected_set_default_chat_permissions_response
        )

    @set_metadata(
        parameters={
            "Chat ID": CHAT_ID,
            "Can Send Polls": CAN_SEND_POLLS,
            "Can Pin Messages": CAN_PIN_MESSAGES,
            "Can Invite Users": CAN_INVITE_USERS,
            "Can Edit Info": CAN_EDIT_INFO,
            "Can Send Messages": CAN_SEND_MESSAGES,
        },
        integration_config_file_path=CONFIG_PATH,
    )
    def test_set_default_chat_permissions_failure(
        self,
        script_session: TelegramSession,
        action_output: MockActionOutput,
        telegram: Telegram,
    ) -> None:
        with telegram.fail_requests():
            SetDefaultChatPermissions.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/setChatPermissions")
        assert request.kwargs["params"] == {
            "chat_id": self.CHAT_ID,
            "can_send_polls": self.CAN_SEND_POLLS,
            "can_pin_messages": self.CAN_PIN_MESSAGES,
            "can_invite_users": self.CAN_INVITE_USERS,
            "can_change_info": self.CAN_EDIT_INFO,
            "can_send_messages": self.CAN_SEND_MESSAGES,
        }

        assert (
            action_output.results.output_message
            == "Could not change the chat permissions. Error: b'Simulated API failure"
            " for SetDefaultChatPermissions'"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED
