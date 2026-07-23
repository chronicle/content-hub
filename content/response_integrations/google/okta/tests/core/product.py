# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pathlib
import abc
from http import HTTPStatus
from typing import Any


class Product(abc.ABC):
    def __init__(self) -> None:
        self.response_status = 202
        self.get_user_responses: dict[str, tuple[int, dict[str, Any] | None]] = {}
        self.clear_session_statuses: dict[str, int] = {}
        self.list_users_responses: dict[str, tuple[int, list[dict[str, Any]]]] = {}

    def set_status(self, status):
        self.response_status = status

    def get_status(self):
        return self.response_status

    def set_clear_user_sessions_response(self, user_id: str, status: int) -> None:
        """
        Set the mock response for clearing a user's sessions.

        Args:
            user_id: The ID of the user.
            status: The HTTP status code to return.
        """
        self.clear_session_statuses[user_id] = status

    def get_clear_user_sessions_status(self, user_id: str) -> int | None:
        """
        Get the mock status for clearing a user's sessions.
        """
        return self.clear_session_statuses.get(user_id)

    def set_get_user_response(
        self,
        user_id: str,
        status: int = HTTPStatus.OK,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Set the mock response for getting a single user.
        """
        self.get_user_responses[user_id] = (status, response_data)

    def get_get_user_response(self, user_id: str) -> tuple[int, dict[str, Any] | None]:
        """Get the mock response for getting a single user."""
        return self.get_user_responses.get(user_id, (HTTPStatus.NOT_FOUND, None))
