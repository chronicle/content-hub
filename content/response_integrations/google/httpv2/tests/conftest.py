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

from typing import Any
import json

from unittest import mock
from pytest_mock import MockerFixture
import pytest
from ..core import AuthenticationManager
from ..core import HTTPV2Manager
from integration_testing.logger import Logger


from pathlib import Path


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict.

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object.
    """
    integration_config = {}
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    integration_config["test_url"] = config["Test URL"]
    integration_config["basic_auth_username"] = config["Basic Auth Username"]
    integration_config["basic_auth_password"] = config["Basic Auth Password"]
    integration_config["api_key_field_name"] = config["API Key Field Name"]
    integration_config["api_key_secret"] = config["API Key Secret"]
    integration_config["auth_api_request_method"] = config[
        "Dedicated Auth API Request Method"
    ]
    integration_config["auth_api_request_url"] = config[
        "Dedicated Auth API Request URL"
    ]
    integration_config["auth_api_request_headers"] = config[
        "Dedicated Auth API Request Headers"
    ]
    integration_config["auth_api_request_body"] = config[
        "Dedicated Auth API Request Body"
    ]
    integration_config["auth_api_request_token_field_name"] = config[
        "Dedicated Auth API Request Token Field Name"
    ]
    integration_config["verify_ssl"] = config["Verify SSL"]
    integration_config["ca_certificate"] = config["CA Certificate"]
    integration_config["restrict_domain"] = config["Restrict Domain"]

    return integration_config


@pytest.fixture(name="auth_params")
def fixture_auth_params(
    load_config: dict[str, Any]
) -> AuthenticationManager.SessionAuthenticationParameters:
    return AuthenticationManager.SessionAuthenticationParameters(**load_config)


@pytest.fixture(name="api_params")
def fixture_api_params(load_config: dict[str, Any]) -> HTTPV2Manager.ApiParameters:
    """Create api params object.

    Args:
        load_config (dict[str, Any]): integration configuration dict object.

    Returns:
        HTTPV2Manager.ApiParameters: api params object.
    """
    return HTTPV2Manager.ApiParameters(
        **{
            "test_url": load_config.get("test_url"),
            "auth_method": load_config.get("auth_method"),
            "restrict_domain": load_config.get("restrict_domain"),
        }
    )


@pytest.fixture(name="session")
def fixture_session(
    auth_params: AuthenticationManager.SessionAuthenticationParameters,
    api_params: HTTPV2Manager.ApiParameters,
    mocker: MockerFixture,
) -> MockerFixture.Mock:
    """Create mock session object to call the API from ApiManager and get the mocked
        response.

    Args:
        auth_params (AuthenticationManager.SessionAuthenticationParameters): session
            auth object
        api_params (HTTPV2Manager.ApiParameters): api params
        mocker (MockerFixture): MockFixture object

    Returns:
        MockerFixture.Mock: Mock object
    """
    mocker.patch("requests.Session", return_value=mocker.Mock())
    chronicle_soar_mock = mock.MagicMock()
    chronicle_soar_mock.get_temp_folder_path.return_value = "/tmp"
    session, _ = AuthenticationManager.get_authenticated_session(
        chronicle_soar=chronicle_soar_mock,
        auth_method=api_params.auth_method,
        auth_params=auth_params,
    )
    return session


@pytest.fixture
def api_manager(
    session: MockerFixture.Mock,
    api_params: HTTPV2Manager.ApiParameters,
) -> HTTPV2Manager.ApiManager:
    """Return ApiManager manager instance.

    Args:
        session (MockerFixture.Mock): Magic mock
        api_params (HTTPV2Manager.ApiParameters): ApiParameters object

    Returns:
        HTTPV2Manager.ApiManager: HTTPV2Manager.ApiManager object
    """
    logger = Logger()
    return HTTPV2Manager.ApiManager(
        session=session,
        api_params=api_params,
        logger=logger,
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
