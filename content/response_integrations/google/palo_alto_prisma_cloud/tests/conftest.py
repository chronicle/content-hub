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
import json
from typing import Any

import pytest
from pytest_mock import MockerFixture
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

from ..core import AuthenticationManager
from ..core import PaloAltoPrismaCloudManager


STATUS_CODES = {
    "SUCCESS": {"status": 200},
}


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, Any]:
    """Load integration configuration from config.json file and return it as dict.

    Returns:
        dict[str, Any]: dictionary object for create auth and api params object.
    """
    integration_config = {}
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_file, "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    integration_config["api_root"] = config["API Root"]
    integration_config["access_key_id"] = config["Access Key ID"]
    integration_config["secret_access_key"] = config["Secret Access Key"]
    integration_config["verify_ssl"] = config["Verify SSL"]
    return integration_config


@pytest.fixture(name="auth_params")
def fixture_auth_params(
    load_config: dict[str, Any],
) -> AuthenticationManager.SessionAuthenticationParameters:
    return AuthenticationManager.SessionAuthenticationParameters(**load_config)


@pytest.fixture(name="api_params")
def fixture_api_params(
    load_config: dict[str, Any],
) -> PaloAltoPrismaCloudManager.ApiManager:
    """Create api params object.

    Args:
        load_config (dict[str, Any]): integration configuration dict object.

    Returns:
        PaloAltoPrismaCloudManager.ApiParameters: api params object.
    """
    return PaloAltoPrismaCloudManager.ApiParameters(**load_config)


@pytest.fixture(name="session")
def fixture_mock_session(mocker: MockerFixture) -> MockerFixture.Mock:
    """Mocked session."""
    mock_session = mocker.Mock()
    mock_session.status_code = STATUS_CODES.get("SUCCESS")

    mocker.patch("requests.Session", return_value=mock_session)
    return mock_session


@pytest.fixture
def api_manager(
    session: MockerFixture.Mock,
    api_params: PaloAltoPrismaCloudManager.ApiParameters,
    mocker: MockerFixture,
) -> PaloAltoPrismaCloudManager.ApiManager:
    """Return PaloAltoPrismaCloudManager instance.

    Args:
        session (MockerFixture.Mock): Magic mock.
        api_params (PaloAltoPrismaCloudManager.ApiParameters): ApiParameters object.
        mocker (MockerFixture): pytest-mock fixture.

    Returns:
        PaloAltoPrismaCloudManager.PaloAltoPrismaCloudManager:
            PaloAltoPrismaCloudManager object.
    """
    logger = mocker.MagicMock()
    return PaloAltoPrismaCloudManager.ApiManager(
        session=session,
        api_parameters=api_params,
        logger=logger,
    )

