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
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockFixture
from _pytest.monkeypatch import MonkeyPatch

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from mandiant_managed_defense.core import AuthenticationManager
from mandiant_managed_defense.core import MandiantMDManager


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object
    """
    integration_config = {}
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    integration_config["api_root"] = config["API Root"]
    integration_config["client_id"] = config["Client ID"]
    integration_config["client_secret"] = config["Client Secret"]
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
) -> MandiantMDManager.ApiParameters:
    """Create api params object.

    Args:
        load_config (dict[str, Any]): integration configuration dict object

    Returns:
        MandiantMDManager.ApiParameters: api params object
    """
    return MandiantMDManager.ApiParameters(**{"api_root": load_config.get("api_root")})


@pytest.fixture(name="session")
def fixture_session(
    auth_params: AuthenticationManager.SessionAuthenticationParameters,
    mocker: MockFixture,
) -> MockFixture.Mock:
    """Create mock session object to call the API from ApiManager and get the mocked
        response

    Args:
        auth_params (AuthenticationManager.SessionAuthenticationParameters): session
            auth object
        mocker (MockerFixture): MockFixture object

    Returns:
        MockerFixture.Mock: Mock object.
    """
    mocker.patch("requests.Session", return_value=mocker.Mock())

    return AuthenticationManager.get_authenticated_session(
        auth_params=auth_params
    )


@pytest.fixture
def api_manager(
    session: MockFixture.Mock,
    api_params: MandiantMDManager.ApiParameters,
    monkeypatch: MonkeyPatch,
) -> MandiantMDManager.ApiManager:
    """Return ApiManager manager instance

    Args:
        session (MockerFixture.Mock): Magic mock
        api_params (MandiantMDManager.ApiParameters): ApiParameters object
        monkeypatch (MonkeyPatch): MonkeyPatch object

    Returns:
        MandiantMDManager.ApiManager object
    """
    logger = MagicMock()
    monkeypatch.setattr(
        SiemplifyConnectorExecution,
        "LOGGER",
        logger
    )
    return MandiantMDManager.ApiManager(
        session=session,
        api_params=api_params,
        chronicle_soar=SiemplifyConnectorExecution,
    )
