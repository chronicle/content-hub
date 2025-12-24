# Copyright 2025 Google LLC
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

from TIPCommon.base.utils import CreateSession
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.logger import Logger

from wiz.core.api_client import WizApiClient, ApiParameters
from .common import CONFIG
from .core.product import Wiz
from .core.session import WizSession


pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(name="wiz")
def wiz_product() -> Wiz:
    yield Wiz()


@pytest.fixture(name="script_session", autouse=True)
def wiz_script_session(
    monkeypatch: pytest.MonkeyPatch,
    wiz: Wiz,
) -> WizSession:
    """Create script session"""
    session: WizSession[MockRequest, MockResponse, Wiz] = WizSession(wiz)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)

    yield session


@pytest.fixture(name="manager")
def wiz_manager(script_session: WizSession) -> WizApiClient:
    """Wiz manager"""
    api_root: str = CONFIG["API Root"]

    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root)

    yield WizApiClient(script_session, api_params, logger)
