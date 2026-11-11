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

from typing import Any
import json

import pytest
from pytest_mock import MockerFixture

from google_cloud_armor.core import AuthenticationManager
from google_cloud_armor.core import GoogleCloudArmorManager
from integration_testing.logger import Logger


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict.

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object.
    """
    integration_config = {}
    with open("config.json", "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    integration_config["api_root"] = config["API Root"]
    integration_config["project_id"] = config["Project ID"]
    integration_config["workload_identity_email"] = config["Workload Identity Email"]
    integration_config["user_service_account"] = config["User Service Account"]
    integration_config["verify_ssl"] = config["Verify SSL"]
    return integration_config


@pytest.fixture(name="auth_params")
def fixture_auth_params(
    load_config: dict[str, Any]
) -> AuthenticationManager.SessionAuthenticationParameters:
    return AuthenticationManager.SessionAuthenticationParameters(**load_config)


@pytest.fixture(name="api_params")
def fixture_api_params(
    load_config: dict[str, Any]
) -> GoogleCloudArmorManager.ApiParameters:
    """Create api params object.

    Args:
        load_config (dict[str, Any]): integration configuration dict object.

    Returns:
        GoogleCloudArmorManager.ApiParameters: api params object.
    """
    load_config.pop("verify_ssl")
    return GoogleCloudArmorManager.ApiParameters(**load_config)


@pytest.fixture(name="session")
def fixture_session(
    auth_params: AuthenticationManager.SessionAuthenticationParameters,
    mocker: MockerFixture,
) -> MockerFixture.Mock:
    """Create mock session object to call the API from ApiManager and get the mocked
        response.

    Args:
        auth_params (AuthenticationManager.SessionAuthenticationParameters): session
            auth object.
        mocker (MockerFixture): MockFixture object.

    Returns:
        MockerFixture.Mock: Mock object.
    """
    mocker.patch(
        "TIPCommon.rest.auth.build_credentials_from_sa", return_value=mocker.Mock()
    )
    mocker.patch("google.auth.credentials.Credentials", return_value=mocker.Mock())
    credentials = AuthenticationManager.get_authentication_credentials_or_raise_error(
        auth_params
    )
    mocker.patch("TIPCommon.rest.gcp.get_http_client", return_value=mocker.Mock())
    return AuthenticationManager.get_authenticated_session(
        credentials=credentials, verify_ssl=auth_params.verify_ssl
    )


@pytest.fixture
def api_manager(
    session: MockerFixture.Mock,
    api_params: GoogleCloudArmorManager.ApiParameters,
) -> GoogleCloudArmorManager.ApiManager:
    """Return ApiManager manager instance.

    Args:
        session (MockerFixture.Mock): Magic mock.
        api_params (GoogleCloudArmorManager.ApiParameters): ApiParameters object.

    Returns:
        GoogleCloudArmorManager.ApiManager: GoogleCloudArmorManager.ApiManager object.
    """
    logger = Logger()
    return GoogleCloudArmorManager.ApiManager(
        session=session,
        api_parameters=api_params,
        logger=logger,
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
