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

from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import cryptography.hazmat.primitives.serialization
import google.auth.transport.requests
import pytest
import soar_sdk  # noqa: F401
import integration_testing.common as integration_testing_common
import integration_testing.set_meta as integration_testing_set_meta
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
    GoogleThreatIntelligenceSdkProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSdkSession,
    GoogleThreatIntelligenceSession,
)

if TYPE_CHECKING:
    import pathlib

pytest_plugins = ("integration_testing.conftest",)

YAML_PARAM_TYPE_MAP: dict[str, int] = {
    "boolean": 0,
    "integer": 1,
    "int": 1,
    "string": 2,
    "password": 3,
    "ip": 4,
    "host": 5,
    "url": 6,
    "domain": 7,
    "email": 8,
}


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
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> GoogleThreatIntelligenceSession:
    """Mock Google Threat Intelligence scripts' session and normalize YAML defs."""
    session = GoogleThreatIntelligenceSession(google_threat_intelligence_product)
    original_get_def = integration_testing_common.get_def_file_content

    def normalized_get_def_file_content(
        def_file_path: pathlib.Path,
    ) -> dict[str, Any]:
        data = original_get_def(def_file_path)
        if (
            isinstance(data, dict)
            and "Parameters" not in data
            and isinstance(data.get("parameters"), list)
        ):
            data["Parameters"] = [
                {
                    "Name": param["name"],
                    "Type": YAML_PARAM_TYPE_MAP.get(
                        str(param.get("type", "string")).lower(), 2
                    ),
                    "DefaultValue": param.get("default_value", ""),
                    "IsMandatory": param.get("is_mandatory", False),
                    "Mode": 2 if param.get("mode") == "script" else 0,
                }
                for param in data["parameters"]
            ]
        return data

    monkeypatch.setattr(
        integration_testing_common,
        "get_def_file_content",
        normalized_get_def_file_content,
    )
    if hasattr(integration_testing_set_meta, "get_def_file_content"):
        monkeypatch.setattr(
            integration_testing_set_meta,
            "get_def_file_content",
            normalized_get_def_file_content,
        )

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
def google_threat_intelligence_product() -> GoogleThreatIntelligenceProduct:
    return GoogleThreatIntelligenceProduct()


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    gti_sdk_product: GoogleThreatIntelligenceSdkProduct,
) -> GoogleThreatIntelligenceSdkSession:
    """Mock the SDK sessions to view request and response history."""
    session = GoogleThreatIntelligenceSdkSession(gti_sdk_product)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session


@pytest.fixture
def gti_sdk_product() -> GoogleThreatIntelligenceSdkProduct:
    return GoogleThreatIntelligenceSdkProduct()
