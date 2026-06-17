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

"""Pytest configuration and fixtures for CyberArk PAM integration tests."""


from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def mock_session() -> Generator[MagicMock, Any, None]:
    """Mock requests.Session object to mock CyberArk API logon and change password endpoints."""
    with patch("requests.Session") as mock_session_cls:
        mock_instance = MagicMock()
        mock_session_cls.return_value = mock_instance

        logon_response = MagicMock()
        logon_response.status_code = 200
        logon_response.text = '"mock-token"'
        logon_response.raise_for_status.return_value = None

        change_response = MagicMock()
        change_response.status_code = 200
        change_response.text = ""
        change_response.raise_for_status.return_value = None

        def mock_post(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                return logon_response
            if "/Change" in url:
                return change_response

            return MagicMock(status_code=404)

        mock_instance.post.side_effect = mock_post

        yield mock_instance
