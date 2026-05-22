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

from enrichment.actions import EnrichEntityFromEventField, EnrichSourceAndDestinations
from enrichment.actions.EnrichEntityFromEventField import ExecutionScope
from enrichment.tests.core.product import EnrichmentProduct
from enrichment.tests.core.session import EnrichmentMockSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


pytest_plugins: tuple[str, ...] = ("integration_testing.conftest",)


def build_alert_mock(adict: dict[str, Any]) -> MagicMock:
    """Build pristine MagicMock alert instance using local descriptors for side-effects."""

    class LocalAlertMock(MagicMock):
        pass

    alert = LocalAlertMock()
    alert.identifier = adict.get("identifier")

    entities = []
    for endict in adict.get("entities", []):
        en = MagicMock()
        en.identifier = endict.get("identifier")
        en.additional_properties = endict.get("additional_properties", {})
        if "alert_identifier" in endict:
            en.alert_identifier = endict["alert_identifier"]
        entities.append(en)
    alert.entities = entities

    def get_events() -> list[Any]:
        if adict.get("fail_events"):
            raise Exception("Simulated failure reading security events")
        events = []
        for evdict in adict.get("security_events", []):
            ev = MagicMock()
            ev.additional_properties = evdict.get("additional_properties", {})
            events.append(ev)
        return events

    LocalAlertMock.security_events = PropertyMock(side_effect=get_events)
    return alert


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
def product() -> EnrichmentProduct:
    """Provide instance of product simulator."""
    return EnrichmentProduct()


@pytest.fixture
def mock_session(product: EnrichmentProduct) -> EnrichmentMockSession:
    """Provide instance of mock session routing to product simulator."""
    return EnrichmentMockSession(product)


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: EnrichmentMockSession,
) -> EnrichmentMockSession:
    """Mock outgoing HTTP REST session."""
    if not use_live_api():
        import requests

        class DummySessionClass(requests.Session):
            def __new__(cls, *args: Any, **kwargs: Any) -> Any:
                return mock_session

        monkeypatch.setattr(CreateSession, "create_session", lambda: mock_session)
        monkeypatch.setattr(requests, "Session", DummySessionClass)

    return mock_session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: EnrichmentMockSession,
) -> EnrichmentMockSession:
    """Mock base Chronicle SOAR Rest session."""
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: mock_session)

    return mock_session


@pytest.fixture
def mock_siemplify(
    product: EnrichmentProduct,
    mock_session: EnrichmentMockSession,
) -> MagicMock:
    """Provide pure MagicMock siemplify double avoiding static top-level class stubs."""

    class LocalSiemplifyMock(MagicMock):
        pass

    siemplify = LocalSiemplifyMock()
    siemplify.session = mock_session
    siemplify.API_ROOT = "https://mock-api-root"
    siemplify.parameters = {"Fields to enrich": "orig_@odata.etag"}
    siemplify.case_id = "case_123"
    siemplify.sdk_config = MagicMock()
    siemplify.sdk_config.one_platform_api_root_uri_format = "https://mock-1p-root/{}"

    class LocalCaseMock(MagicMock):
        pass

    case_mock = LocalCaseMock()

    def get_alerts() -> list[Any]:
        details = product.get_alerts_full_details()
        return [build_alert_mock(adict) for adict in details.get("alerts", [])]

    LocalCaseMock.alerts = PropertyMock(side_effect=get_alerts)
    LocalCaseMock.open_alerts = PropertyMock(side_effect=get_alerts)
    siemplify.case = case_mock

    LocalSiemplifyMock.execution_scope = PropertyMock(
        side_effect=lambda: getattr(
            SiemplifyAction,
            "execution_scope",
            ExecutionScope.Alert,
        )
    )
    LocalSiemplifyMock.current_alert = PropertyMock(
        side_effect=lambda: siemplify.case.alerts[0] if siemplify.case.alerts else None
    )
    LocalSiemplifyMock.target_entities = PropertyMock(
        side_effect=lambda: [
            entity
            for alert in siemplify.case.alerts
            for entity in getattr(alert, "entities", [])
        ]
    )

    siemplify.update_entities.side_effect = lambda *_: mock_session.post(
        "/api/external/v1/sdk/UpdateEntities"
    )
    return siemplify


@pytest.fixture(autouse=True)
def setup_scenario_mocks(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    mock_siemplify: MagicMock,
) -> None:
    """Automatically configure action hooks and translation routines cleanly."""
    monkeypatch.setattr(
        EnrichEntityFromEventField,
        "SiemplifyAction",
        lambda: mock_siemplify,
    )
    monkeypatch.setattr(
        EnrichSourceAndDestinations,
        "SiemplifyAction",
        lambda: mock_siemplify,
    )

    def stub_get_investigator_data(*args: Any, **kwargs: Any) -> SingleJson:
        alert_id = kwargs.get("alert_identifier")
        if not alert_id:
            return {"alerts": []}
        mock_data = request.getfixturevalue("load_mock_data")
        investigator_map = mock_data.get("investigator_data_map", {})
        return investigator_map.get(alert_id, {"alerts": []})

    monkeypatch.setattr(
        EnrichSourceAndDestinations,
        "get_investigator_data",
        stub_get_investigator_data,
    )

    def mock_end_side_effect(
        output_message: str,
        result_value: Any,
        status: Any,
    ) -> None:
        try:
            out_fixture = request.getfixturevalue("action_output")
            payload = {
                "Message": f"{output_message}\n",
                "ResultValue": result_value,
                "ExecutionState": status,
                "ResultObjectJson": json.dumps({"JsonResult": None}),
                "DebugOutput": "",
            }
            out_fixture._out.write(json.dumps(payload))
        except Exception:
            pass

    mock_siemplify.end.side_effect = mock_end_side_effect

    mock_siemplify.parameters = {"Fields to enrich": "orig_@odata.etag"}
