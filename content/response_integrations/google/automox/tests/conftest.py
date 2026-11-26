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
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from automox.core.AutomoxManager import AutomoxManager
from automox.tests.common import CONFIG

if TYPE_CHECKING:
    from collections.abc import Iterator

_MOCK_DATA_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
_MOCK_DATA: dict[str, dict[str, object]] = json.loads(_MOCK_DATA_PATH.read_text(encoding="utf-8"))
_MOCK_DEVICES: list[object] = list(_MOCK_DATA["get_devices"].values())

_MOCK_POLICIES: list[dict[str, object]] = [
    {"id": 101, "name": "Patch Windows", "policy_type_name": "patch", "status": "active", "notes": "Weekly"},
    {"id": 102, "name": "Patch Linux", "policy_type_name": "patch", "status": "inactive", "notes": "Monthly"},
    {"id": 103, "name": "Required Agent", "policy_type_name": "required_software", "status": "active", "notes": ""},
    {"id": 104, "name": "Custom Worklet", "policy_type_name": "custom", "status": "active", "notes": "Audit"},
]

_MOCK_PATCHES: list[dict[str, object]] = [
    {"id": 1, "installed": False, "ignored": False},
    {"id": 2, "installed": False, "ignored": False},
    {"id": 3, "installed": False, "ignored": False},
    {"id": 4, "installed": False, "ignored": False},
    {"id": 5, "installed": True, "ignored": False},
    {"id": 6, "installed": False, "ignored": True},
]


def _build_response(payload: object, status_code: int = 200) -> Mock:
    """Create a mock HTTP response with JSON payload and status code."""
    response = Mock()
    response.status_code = status_code
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


def _mock_get(url: str, **_kwargs: object) -> Mock:
    """Route GET requests for AutomoxManager unit tests."""
    if "/packages" in url:
        return _build_response(_MOCK_PATCHES)
    if "/policies" in url:
        return _build_response(_MOCK_POLICIES)
    if "/queues" in url:
        return _build_response({"errors": ["Not available offline"]}, status_code=404)
    if "/servers" in url:
        return _build_response(_MOCK_DEVICES)
    return _build_response([])


def _mock_post(url: str, **_kwargs: object) -> Mock:
    """Route POST requests for AutomoxManager unit tests."""
    if "/queues" in url:
        return _build_response({"errors": ["Not available offline"]}, status_code=404)
    return _build_response({})


def read_config() -> tuple[str, str]:
    """Read API root and API key from the Automox test configuration."""
    return str(CONFIG["API Root"]), str(CONFIG["API Key"])


@pytest.fixture(scope="module")
def manager_fixture() -> Iterator[AutomoxManager]:
    """Provide an AutomoxManager backed by offline mocked HTTP handlers."""
    api_root, api_key = read_config()
    manager = AutomoxManager(api_root=api_root, api_key=api_key)
    manager.session = Mock(get=_mock_get, post=_mock_post)
    yield manager
