from __future__ import annotations
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import sys

from typing import Any
from unittest.mock import MagicMock

import pytest

from protectwise.actions import GetPcap
from protectwise.core.ProtectwiseManager import ProtectwiseManager
from protectwise.tests import common
from protectwise.tests.core.product import ProtectwiseProduct
from protectwise.tests.core.session import ProtectwiseSession


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "execution_scope(scope): mark test case to run under execution scope",
    )


@pytest.fixture(name="protectwise_product")
def mock_protectwise_product() -> ProtectwiseProduct:
    """Provide a pristine Protectwise product simulator instance."""
    product = ProtectwiseProduct()
    product.seed_events(common.EVENTS_RESPONSE)
    product.seed_pcap(common.EVENT_ID, common.PCAP_BYTES)
    yield product
    product.cleanup()


@pytest.fixture(name="script_session", autouse=True)
def mock_script_session(
    monkeypatch, protectwise_product: ProtectwiseProduct,
) -> ProtectwiseSession:
    session = ProtectwiseSession(protectwise_product)
    """Intercept requests namespace in ProtectwiseManager to route HTTP calls locally."""

    sys.modules[ProtectwiseManager.__module__].requests = session
    yield session


@pytest.fixture(autouse=True)
def configure_execution_scope(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject context scopes dynamically based on custom pytest markers."""
    marker: Any = request.node.get_closest_marker("execution_scope")
    scope_value: Any = GetPcap.ExecutionScope.Alert

    if marker:
        scope_name: str = str(marker.args[0]).strip().title()
        if scope_name == "Case":
            scope_value = GetPcap.ExecutionScope.Case
        elif scope_name == "Alert":
            scope_value = GetPcap.ExecutionScope.Alert

    monkeypatch.setattr(
        GetPcap.SiemplifyAction,
        "execution_scope",
        property(lambda _: scope_value, lambda _self, _val: None),
        raising=False,
    )
    monkeypatch.setattr(
        GetPcap.SiemplifyAction,
        "execution_deadline_unix_time_ms",
        sys.maxsize,
        raising=False,
    )
    monkeypatch.setattr(GetPcap, "unix_now", lambda: -1, raising=False)

    mock_event: MagicMock = common.create_mock_event(
        id_=common.EVENT_ID, name=common.EVENT_NAME
    )
    mock_alert: MagicMock = MagicMock()
    mock_alert.identifier = "alert_123"
    mock_alert.security_events = [mock_event]

    if scope_value == GetPcap.ExecutionScope.Case:
        mock_case: MagicMock = MagicMock()
        mock_case.open_alerts = [mock_alert]
        mock_case.alerts = [mock_alert]
        monkeypatch.setattr(GetPcap.SiemplifyAction, "case", mock_case, raising=False)
    else:
        monkeypatch.setattr(
            GetPcap.SiemplifyAction, "current_alert", mock_alert, raising=False
        )
