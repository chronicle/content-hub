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
from urllib.parse import urljoin

import pytest
import soar_sdk  # noqa: F401
import integration_testing.common as integration_testing_common
import integration_testing.set_meta as integration_testing_set_meta
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from TIPCommon.base.utils import CreateSession

from proofpoint_cloud_threat_response.core.api_client import (
    ApiParameters,
    ProofpointCloudThreatResponseApiClient,
)
from proofpoint_cloud_threat_response.core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
)
from proofpoint_cloud_threat_response.core.constants import AUTH_URL
from proofpoint_cloud_threat_response.tests.common import CONFIG
from proofpoint_cloud_threat_response.tests.core.product import (
    ProofpointCloudThreatResponse,
)
from proofpoint_cloud_threat_response.tests.core.session import (
    ProofpointCloudThreatResponseSession,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
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


@pytest.fixture(name="proofpoint_ctr")
def proofpoint_ctr_product() -> Iterator[ProofpointCloudThreatResponse]:
    yield ProofpointCloudThreatResponse()


@pytest.fixture(name="script_session", autouse=True)
def proofpoint_ctr_script_session(
    monkeypatch: pytest.MonkeyPatch,
    proofpoint_ctr: ProofpointCloudThreatResponse,
) -> Iterator[ProofpointCloudThreatResponseSession]:
    """Create script session and normalize YAML connector parameter metadata."""
    session = ProofpointCloudThreatResponseSession(proofpoint_ctr)
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
        monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
    yield session


@pytest.fixture(name="manager")
def proofpoint_ctr_manager() -> Iterator[ProofpointCloudThreatResponseApiClient]:
    """Build ProofpointCloudThreatResponseApiClient fixture."""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]
    verify_ssl: bool = CONFIG["Verify SSL"]

    logger = Logger()
    api_params = ApiParameters(api_root=api_root)

    auth_session = AuthenticatedSession()
    auth_params_for_session = SessionAuthenticationParameters(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=urljoin(api_root, AUTH_URL),
        verify_ssl=verify_ssl,
    )
    auth_session.authenticate_session(auth_params_for_session)

    yield ProofpointCloudThreatResponseApiClient(
        authenticated_session=auth_session,
        configuration=api_params,
        logger=logger,
    )
