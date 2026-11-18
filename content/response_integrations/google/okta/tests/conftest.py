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

from urllib.parse import parse_qs

import cryptography.hazmat.primitives.serialization
import google.auth.transport.requests
import pytest
import soar_sdk  # noqa: F401
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from TIPCommon.base.utils import CreateSession

from okta.tests.core.product import Product
from okta.tests.core.session import Session

pytest_plugins = ("integration_testing.conftest",)


def _mock_request_params(request: MockRequest) -> dict[str, list[str]]:
    """Backport MockRequest.params for integration_testing 2.2.6."""
    params = parse_qs(request.url.query)
    raw_params = request.kwargs.get("params")
    if isinstance(raw_params, dict):
        for key, value in raw_params.items():
            if key not in params:
                params[key] = [str(value)]
    return params


if not hasattr(MockRequest, "params"):
    MockRequest.params = property(_mock_request_params)  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    okta_product: Product,
) -> Session:
    """Mock Okta scripts' session and get back an object to view request history."""
    session = Session(okta_product)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
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
    return session


@pytest.fixture
def okta_product() -> Product:
    return Product()
