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

import importlib
import json
import pkgutil
import sys
from typing import TYPE_CHECKING

import pytest
import requests
import soar_sdk
import xmltodict

pytest_plugins = ("integration_testing.conftest",)

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

from soar_sdk.SiemplifyAction import SiemplifyAction  # noqa: E402

from service_desk_plus.core.ServiceDeskPlusManager import (  # noqa: E402
    ServiceDeskPlusManager,
)
from service_desk_plus.tests.common import CONFIG, MOCK_PATH  # noqa: E402
from service_desk_plus.tests.core.product import ServiceDeskPlus  # noqa: E402
from service_desk_plus.tests.core.session import ServiceDeskPlusSession  # noqa: E402

if TYPE_CHECKING:
    from integration_testing.requests.response import MockResponse
    from TIPCommon.types import SingleJson


class XmlMockResponse:
    def __init__(self, original_resp: MockResponse) -> None:
        self.original_resp = original_resp
        self.status_code = original_resp.status_code

    @property
    def text(self) -> str:
        try:
            data = json.loads(self.original_resp.text)
            if isinstance(data, dict):
                return xmltodict.unparse(data)
        except json.JSONDecodeError:
            pass
        return self.original_resp.text

    def json(self) -> SingleJson:
        return self.original_resp.json()


@pytest.fixture(scope="module")
def mock_data() -> SingleJson:
    """Load mock data from mock_data.json."""
    return json.loads(MOCK_PATH.read_text(encoding="utf-8"))


class MockAlert:
    def __init__(self) -> None:
        self.external_id = "mock_external_id"
        self.identifier = "mock_identifier"


@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch SiemplifyAction alert metadata and helper methods."""
    monkeypatch.setattr(
        SiemplifyAction,
        "current_alert",
        property(lambda _self: MockAlert()),
    )
    monkeypatch.setattr(SiemplifyAction, "add_tag", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        SiemplifyAction,
        "update_alerts_additional_data",
        lambda *_args, **_kwargs: None,
    )


@pytest.fixture(name="product")
def service_desk_plus_product() -> ServiceDeskPlus:
    """Create a fresh ServiceDeskPlus mock product state."""
    return ServiceDeskPlus()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: ServiceDeskPlus,
) -> ServiceDeskPlusSession:
    """Mock ServiceDeskPlus scripts' HTTP session."""
    session = ServiceDeskPlusSession(product)

    def handle_get(
        url: str,
        params: SingleJson | None = None,
        **kwargs: object,
    ) -> XmlMockResponse:
        resp = session.get(url, params=params, **kwargs)
        return XmlMockResponse(resp)

    def handle_post(
        url: str,
        params: SingleJson | None = None,
        files: SingleJson | None = None,
        **kwargs: object,
    ) -> XmlMockResponse:
        resp = session.post(url, params=params, files=files, **kwargs)
        return XmlMockResponse(resp)

    monkeypatch.setattr(requests, "get", handle_get)
    monkeypatch.setattr(requests, "post", handle_post)
    return session


@pytest.fixture(name="manager")
def service_desk_plus_manager() -> ServiceDeskPlusManager:
    """Create a ServiceDeskPlusManager configured with test credentials."""
    return ServiceDeskPlusManager(CONFIG["Api Root"], CONFIG["Api Key"])

