from __future__ import annotations

import contextlib
import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class Telegram:
    messages: list[SingleJson] = dataclasses.field(default_factory=list)
    _updates_response: SingleJson | None = None
    _chat_details: SingleJson | None = None
    _bot_details: SingleJson | None = None
    _send_doc_response: SingleJson | None = None
    _send_location_response: SingleJson | None = None
    _send_photo_response: SingleJson | None = None
    _ask_question_response: SingleJson | None = None
    _set_default_chat_permissions_response: SingleJson | None = None
    _set_user_permissions_response: SingleJson | None = None
    _fail_requests_active: bool = False

    @contextlib.contextmanager
    def fail_requests(self):
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def add_message(self, message: SingleJson):
        self.messages.append(message)

    def set_updates_response(self, response: SingleJson):
        self._updates_response = response

    def set_chat_details(self, response: SingleJson):
        self._chat_details = response

    def set_bot_details(self, response: SingleJson):
        self._bot_details = response

    def set_send_doc_response(self, response: SingleJson):
        self._send_doc_response = response

    def set_send_location_response(self, response: SingleJson):
        self._send_location_response = response

    def set_send_photo_response(self, response: SingleJson):
        self._send_photo_response = response

    def set_ask_question_response(self, response: SingleJson):
        self._ask_question_response = response

    def set_set_default_chat_permissions_response(self, response: SingleJson):
        self._set_default_chat_permissions_response = response

    def set_set_user_permissions_response(self, response: SingleJson):
        self._set_user_permissions_response = response

    def send_message(self, chat_id: str, text: str) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SendMessage")
        message = {
            "chat_id": chat_id,
            "text": text,
        }
        self.add_message(message)
        return {"ok": True, "result": message}

    def test_connectivity(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetBotDetails")

        if self._bot_details:
            return self._bot_details
        raise Exception(
            "Bot details not set for test_connectivity. Use set_bot_details()."
        )

    def get_chat_details(self, chat_id: str) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure")

        if self._chat_details:
            return self._chat_details
        raise Exception(
            "Chat details not set for get_chat_details. Use set_chat_details()."
        )

    def get_messages(
        self, offset: str | None, allowed_updates: str | None
    ) -> SingleJson:
        # Return pre-set updates response if available
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetMessages")

        if self._updates_response:
            return self._updates_response
        raise Exception(
            "Updates response not set for get_messages. Use set_updates_response()."
        )

    def send_doc(self, chat_id: str, doc_url: str) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SendDocument")
        if self._send_doc_response:
            return self._send_doc_response
        raise Exception(
            "Send document response not set for send_doc. Use set_send_doc_response()."
        )

    def send_location(self, chat_id: str, latitude: str, longitude: str) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Mock API failure")

        if self._send_location_response:
            return self._send_location_response
        raise Exception(
            "Send location response not set for send_location. "
            "Use set_send_location_response()."
        )

    def send_photo(self, chat_id: str, photo_url: str) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SendPhoto")
        if self._send_photo_response:
            return self._send_photo_response
        raise Exception(
            "Send photo response not set for send_photo. Use set_send_photo_response()."
        )

    def ask_question(
        self, chat_id: str, question: str, options: list[str], is_anonymous: bool
    ) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SendPoll")

        if self._ask_question_response:
            return self._ask_question_response
        raise Exception(
            "Ask question response not set for ask_question. "
            "Use set_ask_question_response()."
        )

    def set_default_chat_permissions(
        self,
        chat_id: str,
        can_send_polls: bool,
        can_pin_messages: bool,
        can_invite_users: bool,
        can_change_info: bool,
        can_post_messages: bool,
    ) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SetDefaultChatPermissions")
        if self._set_default_chat_permissions_response:
            return self._set_default_chat_permissions_response
        raise Exception(
            "Set default chat permissions response "
            "not set for set_default_chat_permissions. "
            "Use set_set_default_chat_permissions_response()."
        )

    def set_user_permissions(
        self,
        chat_id: str,
        user_id: str,
        is_anonymous: bool,
        can_change_info: bool,
        can_post_messages: bool,
        can_edit_messages: bool,
        can_delete_messages: bool,
        can_invite_users: bool,
        can_restrict_users: bool,
        can_pin_messages: bool,
        can_promote_members: bool,
    ) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SetUserPermissions")
        if self._set_user_permissions_response:
            return self._set_user_permissions_response
        raise Exception(
            "Set user permissions response not set for set_user_permissions."
            " Use set_set_user_permissions_response()."
        )
