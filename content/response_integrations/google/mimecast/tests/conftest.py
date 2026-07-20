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

import base64
import json
import os
import pathlib
import pkgutil
import sys
from typing import NamedTuple

import pytest
import requests
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

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

# Unify the soar_sdk namespace with the flat namespace for mocks

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Add parent directory and integration directory to sys.path to support internal module resolution
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

int_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)

from TIPCommon.types import SingleJson

from ..core.MimecastManager import MimecastManager
from ..tests.core.product import Mimecast
from ..tests.core.session import MimecastSession
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse


# pylint: disable=redefined-outer-name
class IntegrationParameters(NamedTuple):
    app_id: str
    api_root: str
    app_key: str
    access_key: str
    secret_key: str
    client_id: str
    client_secret: str
    verify_ssl: bool


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        IntegrationParameters: Integration parameters
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, encoding="UTF-8") as f:
        data = f.read()

    config: SingleJson = json.loads(data)
    api_root: str = config["API Root"]
    application_id: str = config["Application ID"]
    application_key: str = config["Application Key"]
    access_key: str = config["Access Key"]
    secret_key: str = config["Secret Key"]
    client_id: str = config["Client ID"]
    client_secret: str = config["Client Secret"]
    verify_ssl: bool = config["Verify SSL"]

    # Validate secret key
    try:
        base64.b64decode(secret_key)
    except Exception as e:
        raise ValueError(f"Invalid secret key in config.json: {e}") from e

    return IntegrationParameters(
        app_id=application_id,
        api_root=api_root,
        app_key=application_key,
        access_key=access_key,
        secret_key=secret_key,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
    )


@pytest.fixture(name="mimecast")
def mimecast_product() -> Mimecast:
    yield Mimecast()


@pytest.fixture(name="script_session", autouse=True)
def mimecast_script_session(
    monkeypatch: pytest.MonkeyPatch,
    mimecast: Mimecast,
) -> MimecastSession:
    """Create script session"""
    session: MimecastSession[MockRequest, MockResponse, Mimecast] = MimecastSession(
        mimecast
    )
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)

    yield session


@pytest.fixture(name="manager")
def mimecast_manager() -> MimecastManager:
    """Mimecast manager"""
    config: IntegrationParameters = read_config()

    yield MimecastManager(
        api_root=config.api_root,
        app_id=config.app_id,
        app_key=config.app_key,
        access_key=config.access_key,
        secret_key=config.secret_key,
        client_id=config.client_id,
        client_secret=config.client_secret,
        verify_ssl=config.verify_ssl,
    )


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
