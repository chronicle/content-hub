
from __future__ import annotations

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import pkgutil
import soar_sdk

import importlib
import pkgutil
import sys

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Save original stdout in case soar_sdk imports hijack it (Siemplify.py calls SiemplifyUtils.override_stdout)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import os
import sys
import pkgutil
import pathlib


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

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

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon

# Add parent directory and integration directory to sys.path to support internal module resolution

import pytest

from TIPCommon.base.utils import CreateSession
from SiemplifyBase import SiemplifyBase
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.logger import Logger
from ..tests.common import CONFIG
from ..tests.core.product import Extrahop
from ..tests.core.session import ExtrahopSession
from ..core.ExtrahopManager import (
    ExtrahopManager,
    ApiParameters,
)


@pytest.fixture(name="extrahop")
def extrahop_product() -> Extrahop:
    yield Extrahop()


@pytest.fixture(name="script_session", autouse=True)
def extrahop_script_session(
    monkeypatch: pytest.MonkeyPatch,
    extrahop: Extrahop,
) -> ExtrahopSession:
    """Create script session"""
    session: ExtrahopSession[MockRequest, MockResponse, Extrahop] = ExtrahopSession(
        extrahop
    )
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)

    yield session


@pytest.fixture(name="manager")
def extrahop_manager(script_session: ExtrahopSession) -> ExtrahopManager:
    """Extrahop manager"""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]

    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, client_id, client_secret)

    yield ExtrahopManager(script_session, api_params, logger)


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


