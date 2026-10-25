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
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from collections import namedtuple
import json
import pytest
import requests


from microsoft_graph_security.core.MicrosoftGraphSecurityManager import (
    MicrosoftGraphSecurityManager,
)

from microsoft_graph_security.tests.common import CONFIG
from microsoft_graph_security.tests.core.session import (
    MicrosoftGraphSecuritySession,
)
from microsoft_graph_security.tests.core.microsoft_graph_security import (
    MicrosoftGraphSecurity,
)
from integration_testing.common import use_live_api


# pylint: disable=redefined-outer-name
INTEGRATION_NAME = "MicrosoftGraphSecurity"
IntegrationParameters = namedtuple(
    "IntegrationParameters",
    [
        "client_id",
        "secret_id",
        "certificate_path",
        "certificate_password",
        "tenant",
        "verify_ssl",
    ],
)


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        _type_: _description_
    """
    with open("config.json", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    client_id = config.get("Client ID")
    secret_id = config.get("Secret ID")
    certificate_path = config.get("Certificate Path")
    certificate_password = config.get("Certificate Password")
    tenant = config.get("Tenant")
    verify_ssl = config.get("Verify SSL")

    return IntegrationParameters(
        client_id,
        secret_id,
        certificate_path,
        certificate_password,
        tenant,
        verify_ssl,
    )


@pytest.fixture(scope="module")
def mock_data() -> dict:
    return json.load(
        open(
            os.path.join(os.path.dirname(__file__), "mock_data.json"),
            encoding="utf-8",
        )
    )


@pytest.fixture
def microsoft_graph_security() -> MicrosoftGraphSecurity:
    yield MicrosoftGraphSecurity()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    microsoft_graph_security: MicrosoftGraphSecurity,
) -> MicrosoftGraphSecuritySession:
    """Mock microsoft graph security scripts' session and get back an
    object to view request history"""
    session: MicrosoftGraphSecuritySession = MicrosoftGraphSecuritySession(
        microsoft_graph_security
    )
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)

    yield session


@pytest.fixture
def microsoft_graph_security_manager() -> MicrosoftGraphSecurityManager:
    """MicrosoftGraphSecurity manager"""
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Secret ID"]
    certificate_path: str = CONFIG["Certificate Path"]
    certificate_password: str = CONFIG["Certificate Password"]
    tenant: str = CONFIG["Tenant"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    if isinstance(verify_ssl, str):
        verify_ssl = verify_ssl.lower() == "true"

    yield MicrosoftGraphSecurityManager(
        client_id,
        client_secret,
        certificate_path,
        certificate_password,
        tenant,
        verify_ssl,
    )


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session):
    return script_session

