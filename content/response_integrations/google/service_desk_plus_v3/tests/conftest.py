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

import json
import pathlib
from typing import Any

import pytest
import requests
import soar_sdk  # noqa: F401
from soar_sdk.SiemplifyAction import SiemplifyAction

from service_desk_plus_v3.core.ServiceDeskPlusManagerV3 import (
    ServiceDeskPlusManagerV3,
)
from service_desk_plus_v3.tests.common import CONFIG
from service_desk_plus_v3.tests.core.product import ServiceDeskPlusV3
from service_desk_plus_v3.tests.core.session import ServiceDeskPlusV3Session

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(scope="module")
def mock_data() -> dict[str, Any]:
    """Load mock data from mock_data.json."""
    mock_data_path = pathlib.Path(__file__).parent / "mock_data.json"
    return json.loads(mock_data_path.read_text(encoding="utf-8"))


class MockAlert:
    """Stub alert object for SiemplifyAction.current_alert."""

    def __init__(self) -> None:
        self.external_id = "mock_external_id"
        self.identifier = "mock_identifier"


@pytest.fixture(autouse=True)
def mock_siemplify(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock SiemplifyAction alert properties and methods."""
    monkeypatch.setattr(
        SiemplifyAction, "current_alert", property(lambda _self: MockAlert())
    )
    monkeypatch.setattr(SiemplifyAction, "add_tag", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        SiemplifyAction,
        "update_alerts_additional_data",
        lambda *_args, **_kwargs: None,
    )


@pytest.fixture(name="product")
def service_desk_plus_v3_product() -> ServiceDeskPlusV3:
    """Return mock ServiceDeskPlusV3 product state."""
    return ServiceDeskPlusV3()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: ServiceDeskPlusV3,
) -> ServiceDeskPlusV3Session:
    """Mock ServiceDeskPlusV3 scripts' session."""
    session = ServiceDeskPlusV3Session(product)

    def handle_get(
        self_session: requests.Session,
        url: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        headers = dict(self_session.headers)
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        mock_resp = session.get(url, params=params, **kwargs)
        real_resp = requests.Response()
        real_resp.status_code = mock_resp.status_code
        real_resp._content = json.dumps(mock_resp.json()).encode("utf-8")
        return real_resp

    def handle_post(
        self_session: requests.Session,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any = None,
        **kwargs: Any,
    ) -> requests.Response:
        headers = dict(self_session.headers)
        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        mock_resp = session.post(url, params=params, data=data, **kwargs)
        real_resp = requests.Response()
        real_resp.status_code = mock_resp.status_code
        real_resp._content = json.dumps(mock_resp.json()).encode("utf-8")
        return real_resp

    monkeypatch.setattr(requests.Session, "get", handle_get)
    monkeypatch.setattr(requests.Session, "post", handle_post)

    return session


@pytest.fixture(name="manager")
def service_desk_plus_v3_manager() -> ServiceDeskPlusManagerV3:
    """Return configured ServiceDeskPlusManagerV3 instance."""
    return ServiceDeskPlusManagerV3(
        CONFIG["Api Root"], CONFIG["Api Key"], verify_ssl=False
    )
