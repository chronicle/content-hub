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

import sys
import types
import pkgutil

# Polyfill/mock imghdr module for Python 3.13+ where it's removed but needed by jira-python client
if "imghdr" not in sys.modules:
    imghdr_mock = types.ModuleType("imghdr")
    imghdr_mock.what = lambda file, h=None: None
    sys.modules["imghdr"] = imghdr_mock

# Polyfill pkgutil.ImpImporter for Python 3.13+ where it's removed but needed by setuptools/pkg_resources
if not hasattr(pkgutil, "ImpImporter"):
    class DummyImpImporter:
        pass
    pkgutil.ImpImporter = DummyImpImporter

import pathlib
import unittest.mock

import google.auth.transport.requests as google_requests
import pytest

from TIPCommon.base.utils import CreateSession
from TIPCommon.types import SingleJson

from scc_enterprise.core.GoogleSecurityCommandCenterManager import (
    GoogleSecurityCommandCenterManager
)
from scc_enterprise.tests.core.product import GoogleSecurityCommandCenter
from scc_enterprise.tests.core.session import (
    GoogleSecurityCommandCenterSession
)
from integration_testing.common import get_def_file_content, use_live_api


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture
def google_security_command_center_product() -> GoogleSecurityCommandCenter:
    yield GoogleSecurityCommandCenter()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_security_command_center_product: GoogleSecurityCommandCenter,
) -> GoogleSecurityCommandCenterSession:
    session = GoogleSecurityCommandCenterSession(google_security_command_center_product)
    """Mock SCCE scripts' session and get back an object to view request history"""

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(
            google_requests,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )
    yield session


@pytest.fixture
def google_security_command_center_manager(
        mocker: unittest.mock.Mock
) -> GoogleSecurityCommandCenterManager:
    """SCCE manager"""
    api_root: str = CONFIG["API Root"]
    verify_ssl: str = CONFIG["Verify SSL"]
    organization_id: str = CONFIG["Organization ID"]
    location_id: str = CONFIG["Location ID"]
    service_account_string: str = CONFIG["Service Account String"]
    workload_identity_email: str = CONFIG["Workload Identity Email"]

    if isinstance(verify_ssl, str):
        verify_ssl: bool = verify_ssl.lower() == "true"

    chronicle_soar: unittest.mock.Mock = mocker.Mock()
    chronicle_soar.get_context_property.return_value = "test@email.com"

    yield GoogleSecurityCommandCenterManager(
        api_root=api_root,
        verify_ssl=verify_ssl,
        organization_id=organization_id,
        location_id=location_id,
        service_account_string=service_account_string,
        chronicle_soar=chronicle_soar,
        workload_identity_email=workload_identity_email,
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
