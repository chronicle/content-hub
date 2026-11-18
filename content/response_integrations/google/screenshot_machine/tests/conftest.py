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
import soar_sdk  # noqa: F401
from integration_testing.common import use_live_api
from TIPCommon.base.utils import CreateSession

from screenshot_machine.tests.core.product import ScreenshotMachine
from screenshot_machine.tests.core.session import ScreenshotMachineSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def screenshot_machine() -> ScreenshotMachine:
    return ScreenshotMachine()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    screenshot_machine: ScreenshotMachine,
) -> ScreenshotMachineSession:
    """Mock ScreenshotMachine session and return it to inspect request history."""
    session = ScreenshotMachineSession(screenshot_machine)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
    return session


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session: ScreenshotMachineSession) -> ScreenshotMachineSession:
    return script_session
