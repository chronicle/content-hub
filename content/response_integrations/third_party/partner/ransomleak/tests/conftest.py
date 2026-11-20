# Copyright 2026 RansomLeak
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
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase

from ransomleak.tests.core.product import RansomLeak
from ransomleak.tests.core.session import RansomLeakSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def ransomleak() -> RansomLeak:
    return RansomLeak()


@pytest.fixture(autouse=True)
def script_session(monkeypatch: pytest.MonkeyPatch, ransomleak: RansomLeak) -> RansomLeakSession:
    """Mock the HTTP session the RansomLeak manager creates and expose request history."""
    session = RansomLeakSession(ransomleak)
    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, ransomleak: RansomLeak) -> RansomLeakSession:
    """Mock the SDK's own session (entity updates, insights)."""
    session = RansomLeakSession(ransomleak)
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session
