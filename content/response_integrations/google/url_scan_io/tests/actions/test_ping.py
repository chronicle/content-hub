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

import pytest
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from url_scan_io.actions import Ping

from ..common import LegacyActionOutput
from ..core.response import MockResponse


def test_ping_success(action_output: LegacyActionOutput) -> None:
    """Tests that Ping succeeds when user/quotas returns 200 OK."""
    Ping.main()

    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is True
    assert action_output.output_message == "Connection Established"


def test_ping_failure(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
) -> None:
    """Tests that Ping reports failure when connectivity check raises an error."""

    class FailingSession:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}
            self.verify: bool = False

        def get(self, _url: str, **_kwargs: object) -> MockResponse:
            return MockResponse(401, {"message": "Invalid API Key"})

    monkeypatch.setattr(
        "url_scan_io.core.UrlScanManager.requests.Session",
        FailingSession,
    )

    Ping.main()

    assert action_output.status == EXECUTION_STATE_FAILED
    assert action_output.is_success is False
    assert "Connection Failed" in (action_output.output_message or "")
