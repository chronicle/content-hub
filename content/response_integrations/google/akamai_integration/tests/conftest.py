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


from collections import namedtuple
import json
import os
import pytest
import requests

from soar_sdk.SiemplifyBase import SiemplifyBase

from akamai_integration.core.api_manager import (
    ApiManager,
    ApiParameters,
)
from akamai_integration.tests.common import CONFIG
from akamai_integration.tests.core.session import AkamaiSession
from akamai_integration.tests.core.product import Akamai as AkamaiProduct
from integration_testing.common import use_live_api
from integration_testing.logger import Logger

INTEGRATION_NAME = "Akamai"

AkamaiConfigParameters = namedtuple(
    "AkamaiConfigParameters",
    [
        "api_root",
        "client_token",
        "client_secret",
        "access_token",
        "verify_ssl",
    ],
)


def read_config() -> AkamaiConfigParameters:
    """Read config.json to get the Akamai integration credentials.

    Returns:
        AkamaiConfigParameters: An object containing API configuration parameters.

    """
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    api_root: str = config.get("Host")
    client_token: str = config.get("Client Token")
    client_secret: str = config.get("Client Secret")
    access_token: str = config.get("Access Token")
    verify_ssl: bool = config.get("Verify SSL", True)

    return AkamaiConfigParameters(
        api_root,
        client_token,
        client_secret,
        access_token,
        verify_ssl,
    )


@pytest.fixture(scope="module")
def mock_data() -> dict:
    """Load mock data from mock_data.json.

    Returns:
        dict: A dictionary containing mock data.

    """
    return json.load(
        open(
            os.path.join(os.path.dirname(__file__), "mock_data.json"),
            encoding="utf-8",
        ),
    )


@pytest.fixture(name="akamai")
def akamai_product() -> AkamaiProduct:
    return AkamaiProduct()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    akamai: AkamaiProduct,
) -> AkamaiSession:
    """Mock Akamai scripts' session and get back an AkamaiSession object
    to view request history.
    """
    session: AkamaiSession = AkamaiSession(akamai)

    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)

    return session


# pylint: disable=redefined-outer-name
@pytest.fixture(name="manager")
def akamai_manager(script_session: AkamaiSession) -> ApiManager:
    return ApiManager(
        session=script_session,
        api_parameters=ApiParameters(api_root=CONFIG["Host"]),
        logger=Logger(),
    )


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch, akamai: AkamaiProduct,
) -> AkamaiSession:
    """Mock the SDK sessions and get it back to view request and response history."""
    session: AkamaiSession = AkamaiSession(akamai)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    return session


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

