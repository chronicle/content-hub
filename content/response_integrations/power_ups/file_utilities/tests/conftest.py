# Copyright 2025 Google LLC
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
import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, PropertyMock

import pytest
from integration_testing.common import use_live_api
from SiemplifyBase import SiemplifyBase
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.base.utils import CreateSession

from file_utilities.core.AttachmentsManager import ExecutionScope
from file_utilities.tests.common import MOCK_CASE_IDENTIFIER
from file_utilities.tests.core.product import FileUtilitiesProduct
from file_utilities.tests.core.session import FileUtilitiesMockSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


pytest_plugins: tuple[str, ...] = ("integration_testing.conftest",)


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "execution_scope(scope): mark test case to run under execution scope",
    )


@pytest.fixture(autouse=True)
def configure_execution_scope(request: pytest.FixtureRequest) -> None:
    """Patch execution scope dynamically based on test markers."""
    if hasattr(SiemplifyAction, "_SiemplifyAction__case"):
        setattr(SiemplifyAction, "_SiemplifyAction__case", None)
    if hasattr(SiemplifyAction, "_SiemplifyAction__current_alert"):
        setattr(SiemplifyAction, "_SiemplifyAction__current_alert", None)
    if hasattr(SiemplifyAction, "_SiemplifyAction__target_entities"):
        setattr(SiemplifyAction, "_SiemplifyAction__target_entities", None)

    marker: Any = request.node.get_closest_marker("execution_scope")
    scope_value = ExecutionScope.Alert

    if marker:
        scope_name: str = str(marker.args[0]).strip().title()
        if scope_name == "Case":
            scope_value = ExecutionScope.Case
        elif scope_name == "Alert":
            scope_value = ExecutionScope.Alert

    setattr(SiemplifyAction, "execution_scope", scope_value)


@pytest.fixture
def load_mock_data() -> SingleJson:
    """Load declarative mock data dynamically."""
    mock_data_path: str = os.path.join(os.path.dirname(__file__), "mock_data.json")
    with open(mock_data_path, "r") as f:
        return json.load(f)


@pytest.fixture
def product() -> FileUtilitiesProduct:
    """Provide instance of product simulator."""
    return FileUtilitiesProduct()


@pytest.fixture
def mock_session(product: FileUtilitiesProduct) -> FileUtilitiesMockSession:
    """Provide instance of mock session routing to product simulator."""
    return FileUtilitiesMockSession(product)


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: FileUtilitiesMockSession,
) -> FileUtilitiesMockSession:
    """Mock outgoing HTTP REST session."""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: mock_session)
        monkeypatch.setattr("requests.Session", lambda: mock_session)

    return mock_session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: FileUtilitiesMockSession,
) -> FileUtilitiesMockSession:
    """Mock base Chronicle SOAR Rest session."""
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: mock_session)

    return mock_session


class MockAttachmentRecordStub:
    """Stub object simulating bytes buffer returned by get_attachment."""

    def __init__(self, content: bytes) -> None:
        self._content: bytes = content

    def getvalue(self) -> bytes:
        return self._content


@pytest.fixture
def mock_siemplify(
    product: FileUtilitiesProduct,
    mock_session: FileUtilitiesMockSession,
) -> MagicMock:
    """Provide fully initialized mock Siemplify object routing to product simulator."""

    class LocalSiemplifyMock(MagicMock):
        pass

    siemplify = LocalSiemplifyMock()
    siemplify.case.alerts = []
    del siemplify.case.open_alerts
    siemplify.case.identifier = MOCK_CASE_IDENTIFIER
    siemplify.session = mock_session
    siemplify.API_ROOT = "https://mock-api-root"
    siemplify.sdk_config.one_platform_api_root_uri_format = "https://mock-1p-root/{}"
    siemplify.get_attachment.side_effect = lambda evidence_id: MockAttachmentRecordStub(
        product.get_attachment_blob(evidence_id)
    )
    LocalSiemplifyMock.execution_scope = PropertyMock(
        side_effect=lambda: getattr(
            SiemplifyAction,
            "execution_scope",
            ExecutionScope.Alert,
        )
    )
    return siemplify
