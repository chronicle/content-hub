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
import os
import sys
import pkgutil
import pathlib


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

import importlib

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

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = os.path.dirname(soar_sdk.__file__)
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Add parent directory and integration directory to sys.path to support internal module resolution
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
int_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)



import json
from collections import namedtuple
import cryptography.hazmat.primitives.serialization
import google
import pytest
from pytest_mock import MockerFixture
from google.oauth2 import service_account

from ..core import GoogleFormsAuth, GoogleFormsManager
from ..tests.core.product import GoogleForms
from ..tests.core.session import GoogleFormsSession
from integration_testing.common import use_live_api
from integration_testing.logger import Logger


STATUS_CODES = {
    "SUCCESS": {"status": 200},
}

# pylint: disable=redefined-outer-name


@pytest.fixture(name="load_config")
def fixture_load_config() -> dict[str, str | bool]:
    """
    Load integration configuration from config.json file and return it as a dictionary.

    Returns:
        dict[str, str | bool]: Configuration dictionary.
    """
    integration_config = {}
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)

    integration_config["service_account_json"] = config["Service Account JSON"]
    integration_config["delegated_email"] = config["Delegated Email"]
    integration_config["verify_ssl"] = config["Verify SSL"]

    return integration_config


@pytest.fixture(name="auth_manager")
def fixture_auth_manager(
    mocker: MockerFixture, load_config: dict[str, str | bool]
) -> GoogleFormsAuth.GoogleFormsAuthManager:
    """
    Create an instance of GoogleFormsAuthManager.

    Args:
        load_config (dict[str, str | bool]): Loaded configuration.

    Returns:
        GoogleFormsAuthManager: Auth manager instance.
    """

    mock_credentials = mocker.create_autospec(service_account.Credentials)
    mock_credentials.return_value = "mocked_token"

    mocker.patch(
        "google.oauth2.service_account.Credentials", return_value=mock_credentials
    )
    return GoogleFormsAuth.GoogleFormsAuthManager(
        service_account_creds=load_config["service_account_json"],
        delegated_email=load_config["delegated_email"],
        verify_ssl=load_config["verify_ssl"],
    )


@pytest.fixture
def google_forms() -> GoogleForms:
    return GoogleForms()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_forms: GoogleForms,
) -> GoogleFormsSession:
    """Mock Google Form session to view request history."""
    session: GoogleFormsSession = GoogleFormsSession(google_forms)

    if not use_live_api():
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            cryptography.hazmat.primitives.serialization,
            "load_pem_private_key",
            lambda *_, **__: "private_key",
        )
        monkeypatch.setattr(
            service_account.Credentials,
            "refresh",
            lambda *args, **kwargs: "refresh",
        )

    yield session


@pytest.fixture
def api_manager(
    script_session: MockerFixture.Mock,
) -> GoogleFormsManager.GoogleFormsManager:
    """Return GoogleFormsManager instance.

    Args:
        script_session (MockerFixture.Mock): A mocked session object used
            to simulate API requests and responses.

    Returns:
        GoogleFormsManager.GoogleFormsManager:
            GoogleFormsManager object.
    """
    logger = Logger()
    IntegrationParameters = namedtuple("IntegrationParameters", ["siemplify_logger"])
    return GoogleFormsManager.GoogleFormsManager(
        session=script_session, params=IntegrationParameters(siemplify_logger=logger)
    )


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


