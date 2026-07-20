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

import importlib
import pkgutil
import sys

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

import pytest
from ..tests.core.product import ServiceDeskPlus
from ..tests.core.session import ServiceDeskPlusSession
from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager
import requests

@pytest.fixture(name="product")
def service_desk_plus_fixture() -> ServiceDeskPlus:
    return ServiceDeskPlus()

import xmltodict
import json

class XmlMockResponse:
    def __init__(self, original_resp):
        self.original_resp = original_resp
        self.status_code = original_resp.status_code
        self.headers = original_resp.headers

    @property
    def text(self):
        try:
            # MockResponse converts dict to JSON string in .text
            data = json.loads(self.original_resp.text)
            if isinstance(data, dict):
                xml_str = xmltodict.unparse(data)
                return xml_str
        except (json.JSONDecodeError, TypeError):
            pass

        return self.original_resp.text

    def json(self):
        return self.original_resp.json()


@pytest.fixture(name="script_session", autouse=True)
def script_session_fixture(
    monkeypatch: pytest.MonkeyPatch, product: ServiceDeskPlus
) -> ServiceDeskPlusSession:
    session = ServiceDeskPlusSession(product)
    original_get = requests.get
    original_post = requests.post
    
    def mock_get(url, *args, **kwargs):
        if "sdpapi" in url:
            return XmlMockResponse(session.get(url, *args, **kwargs))
        return original_get(url, *args, **kwargs)
        
    def mock_post(url, *args, **kwargs):
        if "sdpapi" in url:
            return XmlMockResponse(session.post(url, *args, **kwargs))
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

