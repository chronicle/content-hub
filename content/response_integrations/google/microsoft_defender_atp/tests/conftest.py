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
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import pytest
from soar_sdk.SiemplifyBase import SiemplifyBase
import requests
from TIPCommon.base.utils import CreateSession
from microsoft_defender_atp.core.MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPManager,
)
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.logger import Logger
from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)


@pytest.fixture(name="microsoft_defender_atp")
def microsoft_defender_atp_product() -> MicrosoftDefenderATP:
    yield MicrosoftDefenderATP()


@pytest.fixture(name="script_session", autouse=True)
def microsoft_defender_atp_script_session(
    monkeypatch: pytest.MonkeyPatch,
    microsoft_defender_atp: MicrosoftDefenderATP,
) -> MicrosoftDefenderATPSession:
    session = MicrosoftDefenderATPSession(microsoft_defender_atp)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(requests, "post", session.post)
        # Override SiemplifyBase.create_session so siemplify.session uses the mock
        # (this allows internal SDK calls like UpdateEntities to be routed correctly)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    yield session




@pytest.fixture(name="_script_session")
def microsoft_defender_atp_script_session_alias(
    script_session: MicrosoftDefenderATPSession,
) -> MicrosoftDefenderATPSession:
    """Alias for script_session used by tests that discard the session object."""
    return script_session


@pytest.fixture(name="_microsoft_defender_atp")
def microsoft_defender_atp_product_alias(
    microsoft_defender_atp: MicrosoftDefenderATP,
) -> MicrosoftDefenderATP:
    """Alias for microsoft_defender_atp used by tests that discard the product."""
    return microsoft_defender_atp

@pytest.fixture(name="manager")
def manager_fixture(
    script_session: MicrosoftDefenderATPSession,
) -> MicrosoftDefenderATPManager:
    """
    Fixture for the MicrosoftDefenderATPManager.
    """
    logger = Logger()
    yield MicrosoftDefenderATPManager(
        session=script_session, siemplify_logger=logger, **common.CONFIG
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
