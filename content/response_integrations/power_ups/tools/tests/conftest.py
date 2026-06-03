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
import pathlib
from typing import TYPE_CHECKING, Any

import pytest
from integration_testing.common import use_live_api
from SiemplifyBase import SiemplifyBase
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.base.utils import CreateSession

from .core.product import Tools
from .core.session import ToolsSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "execution_scope(scope): mark a test case to execute "
        "under a specific execution scope",
    )


@pytest.fixture(autouse=True)
def configure_execution_scope(request: pytest.FixtureRequest) -> None:
    """Automatically patch SiemplifyAction.execution_scope.

    Scope is based on the test's execution_scope marker.
    """
    if hasattr(SiemplifyAction, "_SiemplifyAction__case"):
        setattr(SiemplifyAction, "_SiemplifyAction__case", None)
    if hasattr(SiemplifyAction, "_SiemplifyAction__current_alert"):
        setattr(SiemplifyAction, "_SiemplifyAction__current_alert", None)
    if hasattr(SiemplifyAction, "_SiemplifyAction__target_entities"):
        setattr(SiemplifyAction, "_SiemplifyAction__target_entities", None)

    marker = request.node.get_closest_marker("execution_scope")
    scope_value = 1

    if marker:
        scope_name = str(marker.args[0]).strip().title()
        if scope_name == "Case":
            scope_value = 2
        elif scope_name == "Alert":
            scope_value = 1

    setattr(SiemplifyAction, "execution_scope", scope_value)


@pytest.fixture(autouse=True)
def reset_tools_state(tools: Tools) -> None:
    """Explicitly reset simulated Tools product state to default values.

    Resets state before each test runs.
    """
    tools.case_title = "Original Title"
    tools.workflows = []
    tools.case_metadata = {}
    tools.alerts_full_details = []


class MockEntity:
    """Minimal representation of Entity matching standard SDK properties."""

    def __init__(
        self,
        identifier: str,
        entity_type: str = "ADDRESS",
        additional_properties: SingleJson | None = None,
    ) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = additional_properties or {}

    def _update_internal_properties(self) -> None:
        pass

    def to_dict(self) -> SingleJson:
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
        }


@pytest.fixture
def load_mock_data() -> SingleJson:
    """Helper to load mock JSON payloads dynamically."""
    mock_data_path = pathlib.Path(__file__).parent / "mock_data.json"
    with open(mock_data_path, "r") as f:
        return json.load(f)


@pytest.fixture
def tools() -> Tools:
    return Tools()


@pytest.fixture
def tools_session(tools: Tools) -> ToolsSession:
    """Shared ToolsSession instance across testing fixtures."""
    return ToolsSession(tools)


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    tools_session: ToolsSession,
) -> ToolsSession:
    """Mock Tools scripts' session and get back an object to view request history"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: tools_session)
        monkeypatch.setattr("requests.Session", lambda: tools_session)

    return tools_session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    tools_session: ToolsSession,
) -> ToolsSession:
    """Mock SDK base session to cleanly bind ToolsSession.

    Binds ToolsSession for internal SDK REST queries.
    """
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: tools_session)

    return tools_session
