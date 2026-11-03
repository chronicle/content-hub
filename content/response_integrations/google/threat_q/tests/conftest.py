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

from __future__ import annotations

import json
import pathlib
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
import requests

from threat_q.core.ThreatQManager import ThreatQManager, ApiToken


def get_json_file_content(path: pathlib.Path) -> dict:
    """Loads JSON file content."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = get_def_file_content(CONFIG_PATH)


@pytest.fixture
def threatq_manager(monkeypatch: pytest.MonkeyPatch) -> Generator[ThreatQManager]:
    """Provides a mocked ThreatQManager instance.

    Yields:
        ThreatQManager: An initialized manager instance with mocked dependencies.
    """
    mock_session_instance: MagicMock = MagicMock(spec=requests.Session)
    mock_session_instance.headers = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [], "total": 0}
    mock_response.content = b"{}"

    mock_response.raise_for_status.return_value = None

    mock_session_instance.request.return_value = mock_response
    mock_session_instance.get.return_value = mock_response
    mock_session_instance.post.return_value = mock_response
    mock_session_instance.put.return_value = mock_response
    mock_session_instance.delete.return_value = mock_response

    monkeypatch.setattr(requests, "Session", lambda: mock_session_instance)

    mock_api_token = ApiToken(
        access_token="mock_access_token",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="mock_refresh_token"
    )
    monkeypatch.setattr(
        ThreatQManager,
        "get_connection_token",
        lambda self: mock_api_token
    )

    manager = ThreatQManager(
        server_address=CONFIG["ServerAddress"],
        client_id=CONFIG["ClientId"],
        username=CONFIG["Username"],
        password=CONFIG["Password"],
    )

    yield manager
