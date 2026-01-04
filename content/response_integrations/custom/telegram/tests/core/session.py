from __future__ import annotations

from typing import Any

from .product import Telegram
from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class TelegramSession(MockSession[MockRequest, MockResponse, Telegram]):
    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.send_message,
            self.get_me,
            self.get_chat,
            self.get_updates,
            self.send_document,
            self.send_location,
            self.send_photo,
            self.send_poll,
            self.set_chat_permissions,
            self.set_user_permissions,
        ]

    @router.get(r"/bot\S+/sendMessage")
    def send_message(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            text = payload["text"]

            response_data = self._product.send_message(chat_id, text)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/getMe")
    def get_me(self, request: MockRequest) -> MockResponse:
        try:
            response_data = self._product.test_connectivity()
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/getChat")
    def get_chat(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            response_data = self._product.get_chat_details(chat_id)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/getUpdates")
    def get_updates(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            offset = payload.get("offset")
            allowed_updates = payload.get("allowed_updates")
            response_data = self._product.get_messages(offset, allowed_updates)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/sendDocument")
    def send_document(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            doc_url = payload["document"]
            response_data = self._product.send_doc(chat_id, doc_url)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/sendLocation")
    def send_location(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            latitude = payload["latitude"]
            longitude = payload["longitude"]
            response_data = self._product.send_location(chat_id, latitude, longitude)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/sendPhoto")
    def send_photo(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            photo_url = payload["photo"]
            response_data = self._product.send_photo(chat_id, photo_url)
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/sendPoll")
    def send_poll(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            question = payload["question"]
            options = payload["options"]
            is_anonymous = payload["is_anonymous"]
            response_data = self._product.ask_question(
                chat_id, question, options, is_anonymous
            )
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/setChatPermissions")
    def set_chat_permissions(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            can_send_polls = payload["can_send_polls"]
            can_pin_messages = payload["can_pin_messages"]
            can_invite_users = payload["can_invite_users"]
            can_change_info = payload["can_change_info"]
            can_send_messages = payload["can_send_messages"]
            response_data = self._product.set_default_chat_permissions(
                chat_id,
                can_send_polls,
                can_pin_messages,
                can_invite_users,
                can_change_info,
                can_send_messages,
            )
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r"/bot\S+/promoteChatMember")
    def set_user_permissions(self, request: MockRequest) -> MockResponse:
        try:
            payload: dict[str, Any] = get_request_payload(request)
            chat_id = payload["chat_id"]
            user_id = payload["user_id"]
            is_anonymous = payload["is_anonymous"]
            can_change_info = payload["can_change_info"]
            can_post_messages = payload["can_post_messages"]
            can_edit_messages = payload["can_edit_messages"]
            can_delete_messages = payload["can_delete_messages"]
            can_invite_users = payload["can_invite_users"]
            can_restrict_users = payload["can_restrict_users"]
            can_pin_messages = payload["can_pin_messages"]
            can_promote_members = payload["can_promote_members"]
            response_data = self._product.set_user_permissions(
                chat_id,
                user_id,
                is_anonymous,
                can_change_info,
                can_post_messages,
                can_edit_messages,
                can_delete_messages,
                can_invite_users,
                can_restrict_users,
                can_pin_messages,
                can_promote_members,
            )
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)
