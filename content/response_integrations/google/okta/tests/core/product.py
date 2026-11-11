from __future__ import annotations
import abc

from http import HTTPStatus
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import JSON


def _get_paginated_page(
    store: dict[str, list[tuple[int, JSON]]],
    user_id: str | None,
    page_index: int,
) -> tuple[int, JSON, bool]:
    """Look up a single page from a per-user paginated store."""
    pages = store.get(user_id) if user_id else None
    if not pages:
        error: JSON = {
            "errorCode": "E0000007",
            "errorSummary": f"Not found: Resource not found: {user_id} (User)",
            "errorCauses": [],
        }
        return HTTPStatus.NOT_FOUND, error, False

    if page_index >= len(pages):
        error = {
            "errorCode": "E0000031",
            "errorSummary": "Invalid pagination cursor",
            "errorCauses": [],
        }
        return HTTPStatus.BAD_REQUEST, error, False

    status, body = pages[page_index]
    return status, body, page_index + 1 < len(pages)


class Product(abc.ABC):
    def __init__(self) -> None:
        self.response_status = 202
        self.get_user_responses: dict[str, tuple[int, dict[str, Any] | None]] = {}
        self.clear_session_statuses: dict[str, int] = {}
        self.list_users_responses: dict[str, tuple[int, list[dict[str, Any]]]] = {}
        self.user_groups_pages: dict[str, list[tuple[int, JSON]]] = {}
        self.user_roles_pages: dict[str, list[tuple[int, JSON]]] = {}

    def set_status(self, status):
        self.response_status = status

    def get_status(self):
        return self.response_status

    def set_user_groups_pages(self, user_id: str, pages: list[tuple[int, JSON]]) -> None:
        """Set the paginated mock responses for listing a user's groups."""
        self.user_groups_pages[user_id] = pages

    def get_user_groups_page(self, user_id: str | None, page_index: int) -> tuple[int, JSON, bool]:
        """Get a single page of the mock user-groups response."""
        return _get_paginated_page(self.user_groups_pages, user_id, page_index)

    def set_user_roles_pages(self, user_id: str, pages: list[tuple[int, JSON]]) -> None:
        """Set the paginated mock responses for listing a user's roles."""
        self.user_roles_pages[user_id] = pages

    def get_user_roles_page(self, user_id: str | None, page_index: int) -> tuple[int, JSON, bool]:
        """Get a single page of the mock user-roles response."""
        return _get_paginated_page(self.user_roles_pages, user_id, page_index)

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
