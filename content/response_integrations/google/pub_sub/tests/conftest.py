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

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import pkgutil
import soar_sdk
changed = True
while changed:
    changed = False
    for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
        if name not in sys.modules:
            try:
                sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
                changed = True
            except Exception:
                pass
import os
import sys
import pkgutil
import pathlib


import pytest
import requests
import pathlib

import soar_sdk

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ..tests.core.product import Product
from ..tests.core.session import ApiSession
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
import requests

def mock_extract_configuration_param(self, provider_name, param_name, default_value=None, input_type=str, is_mandatory=False, print_value=False):
    from ..tests.common import CONFIG
    return CONFIG.get(param_name, default_value)

SiemplifyConnectorExecution.extract_configuration_param = mock_extract_configuration_param
SiemplifyConnectorExecution.disable_overflow = property(lambda self: False)
SiemplifyConnectorExecution.environment_field_name = property(lambda self: "env_field")
SiemplifyConnectorExecution.environment_regex_pattern = property(lambda self: ".*")

from TIPCommon.base.connector import Connector
Connector.is_overflow_alert = lambda self, alert_info: False
Connector.is_overflowed = lambda self, alert_info, env: False

from ..connectors.PubSubMessagesConnector import PubSubMessagesConnector
PubSubMessagesConnector.is_overflow_alert = lambda self, alert_info: False

import google.oauth2.credentials

@pytest.fixture(name="product", autouse=True)
def product_fixture() -> Product:
    return Product()

@pytest.fixture(name="gcloud_pubsub_script_session", autouse=True)
def script_session_fixture(
    monkeypatch: pytest.MonkeyPatch, product: Product
) -> ApiSession:
    session = ApiSession(product)
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.setattr(requests.sessions, "Session", lambda: session)
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: session.request("GET", url, **kwargs))
    def mock_authorized_session(credentials, *args, **kwargs):
        session.credentials = credentials
        return session
    monkeypatch.setattr("pub_sub.core.PubSubAuthManager.AuthorizedSession", mock_authorized_session)
    monkeypatch.setattr("pub_sub.core.PubSubAuthManager.get_workload_sa_email", lambda *args, **kwargs: "mocked-sa@domain.com")
    return session

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(autouse=True)
def mock_google_adc(mocker):
    """Mock the ADC to prevent DefaultCredentialsError in CI environments."""
    mock_creds = mocker.Mock()
    mock_creds.universe_domain = "googleapis.com"
    mocker.patch("google.auth.default", return_value=(mock_creds, "test-project"))
    mocker.patch("TIPCommon.rest.auth.get_adc", return_value=(mock_creds, "test-project"))
    try:
        mocker.patch("core.utils.get_adc", return_value=(mock_creds, "test-project"))
    except Exception:
        pass
    try:
        mocker.patch("core.GoogleGmailUtils.get_adc", return_value=(mock_creds, "test-project"))
    except Exception:
        pass

