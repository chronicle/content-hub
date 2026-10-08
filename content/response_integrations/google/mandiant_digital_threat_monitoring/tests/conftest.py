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
import pathlib
import pkgutil
import importlib
import logging
import soar_sdk

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
parent_dir = str(pathlib.Path(__file__).resolve().parents[2])
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
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
from pytest_mock import MockFixture

from mandiant_digital_threat_monitoring.core import AuthenticationManager
from mandiant_digital_threat_monitoring.core import MandiantDTMManager
sys.modules["MandiantDTMManager"] = MandiantDTMManager


class Logger:
    """Mocks a logger object with info, error, warn and debug methods"""

    def __init__(self, *_, **__) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.log_rows: list[str] = []

    def debug(self, msg: str, *_, **__) -> None:
        self.log_rows.append(msg)

    def info(self, msg: str, *_, **__) -> None:
        self.log_rows.append(msg)

    def warn(self, msg: str, *_, **__) -> None:
        self.log_rows.append(msg)

    def error(self, msg: str, *_, **__) -> None:
        self.log_rows.append(msg)

    def exception(self, ex: Exception, *_, **__) -> None:
        self.log_rows.append(str(ex))


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object
    """
    integration_config = {}
    config_path = pathlib.Path(__file__).parent / "config.json"
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
) -> MandiantDTMManager.ApiParameters:
    """Create api params object.

    Args:
        load_config (dict[str, Any]): integration configuration dict object

    Returns:
        MandiantDTMManager.ApiParameters: api params object
    """
    return MandiantDTMManager.ApiParameters(**{"api_root": load_config.get("api_root")})


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
    api_params: MandiantDTMManager.ApiParameters,
) -> MandiantDTMManager.ApiManager:
    """Return ApiManager manager instance

    Args:
        session (MockerFixture.Mock): Magic mock
        api_params (MandiantDTMManager.ApiParameters): ApiParameters object

    Returns:
        MandiantDTMManager.ApiManager: MandiantDTMManager.ApiManager object
    """
    logger = Logger()
    return MandiantDTMManager.ApiManager(
        session=session,
        api_params=api_params,
        logger=logger,
    )
