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

import pytest
from service_desk_plus.tests.core.product import ServiceDeskPlus
from service_desk_plus.tests.core.session import ServiceDeskPlusSession
from service_desk_plus.core.ServiceDeskPlusManager import ServiceDeskPlusManager
import requests

@pytest.fixture(name="product")
def service_desk_plus_fixture() -> ServiceDeskPlus:
    return ServiceDeskPlus()

@pytest.fixture(name="script_session", autouse=True)
def script_session_fixture(
    monkeypatch: pytest.MonkeyPatch, product: ServiceDeskPlus
) -> ServiceDeskPlusSession:
    session = ServiceDeskPlusSession(product)
    original_get = requests.get
    original_post = requests.post
    
    def mock_get(url, *args, **kwargs):
        if "sdpapi" in url:
            return session.get(url, *args, **kwargs)
        return original_get(url, *args, **kwargs)
        
    def mock_post(url, *args, **kwargs):
        if "sdpapi" in url:
            return session.post(url, *args, **kwargs)
        return original_post(url, *args, **kwargs)
        
    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr(requests, "Session", lambda: session)
    return session

@pytest.fixture(name="manager")
def manager_fixture(script_session: ServiceDeskPlusSession) -> ServiceDeskPlusManager:
    return ServiceDeskPlusManager(
        api_url_base="https://test.com/sdpapi/",
        api_key="fake_key",
    )

@pytest.fixture(autouse=True)
def mock_siemplify_methods(monkeypatch):
    monkeypatch.setattr(soar_sdk.SiemplifyAction.SiemplifyAction, "add_tag", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr(soar_sdk.SiemplifyAction.SiemplifyAction, "update_alerts_additional_data", lambda *args, **kwargs: None, raising=False)

import os
import sys
import pkgutil
import pathlib


import pytest
import requests

import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

