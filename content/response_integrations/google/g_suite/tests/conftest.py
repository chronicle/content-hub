from __future__ import annotations
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

import pathlib

import google.auth.transport.requests
import pytest
import requests

from TIPCommon.types import SingleJson

from g_suite.core.datamodels import IntegrationParameters
import g_suite.core.GSuiteManager
from g_suite.core.GSuiteAuth import GSuiteAuthManager
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.tests.core.session import ApiSession
from g_suite.tests.core.product import Product
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

pytest_plugins = ("Tests.mocks.ci_fixtures",)


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


# pylint: disable=redefined-outer-name
@pytest.fixture
def product() -> Product:
    return Product()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: Product,
) -> ApiSession:
    session = ApiSession(product)
    """Mock Gcloud API session and get back an object to view request history"""
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            g_suite.Managers.GSuiteAuth,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )
    yield session




@pytest.fixture
def _script_session(script_session: ApiSession) -> ApiSession:
    """Alias for script_session used by tests that discard the session object."""
    return script_session


@pytest.fixture
def _product(product: Product) -> Product:
    """Alias for product used by tests that discard the product object."""
    return product
@pytest.fixture
def gsuite_api_manager() -> GSuiteManager:
    """GoogleGmailApiManager manager"""
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    delegated_email = CONFIG["Delegated Email"]
    service_account_creds = CONFIG["Service Account JSON"]
    auth_manager = GSuiteAuthManager(
        service_account_creds=service_account_creds,
        verify_ssl=verify_ssl,
        delegated_email=delegated_email,
        workload_identity_email=workload_identity_email,
    )

    return GSuiteManager(
        session=auth_manager.prepare_session(),
        params=IntegrationParameters(Logger())
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
