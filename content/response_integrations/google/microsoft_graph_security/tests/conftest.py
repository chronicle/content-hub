from __future__ import annotations

import sys
import os
import pkgutil
import pathlib
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

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import os
import pkgutil
import soar_sdk

import pathlib


import pytest
import requests

import soar_sdk

# Add the integration root directory to sys.path so tests can import actions and core natively
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from tests.core.microsoft_graph_security import MicrosoftGraphSecurity
from tests.core.session import MicrosoftGraphSecuritySession
from core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager

@pytest.fixture(name="microsoft_graph_security", autouse=True)
def product_fixture() -> MicrosoftGraphSecurity:
    return MicrosoftGraphSecurity()

@pytest.fixture(name="product", autouse=True)
def product_alias(microsoft_graph_security: MicrosoftGraphSecurity) -> MicrosoftGraphSecurity:
    return microsoft_graph_security

@pytest.fixture(name="script_session", autouse=True)
def script_session_fixture(
    monkeypatch: pytest.MonkeyPatch, microsoft_graph_security: MicrosoftGraphSecurity
) -> MicrosoftGraphSecuritySession:
    session = MicrosoftGraphSecuritySession(microsoft_graph_security)
    monkeypatch.setattr(requests, "Session", lambda: session)
    return session

@pytest.fixture(name="microsoft_graph_security_manager")
def microsoft_graph_security_manager_fixture(
    script_session: MicrosoftGraphSecuritySession
) -> MicrosoftGraphSecurityManager:
    return MicrosoftGraphSecurityManager(
        tenant="tenant",
        client_id="client_id",
        client_secret="client_secret",
        certificate_path="",
        certificate_password="",
        verify_ssl=False
    )

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

