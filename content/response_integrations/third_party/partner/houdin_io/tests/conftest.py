from __future__ import annotations

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
import requests
from integration_testing.set_meta import set_metadata
from soar_sdk.SiemplifyDataModel import DomainEntityInfo

from .common import CONFIG_PATH
from .mock_session import HoudinSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(autouse=True)
def houdin(monkeypatch: pytest.MonkeyPatch) -> HoudinSession:
    """Every requests.Session the manager opens is the mocked Houdin."""
    session = HoudinSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.setattr(requests, "session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda *_: None)


@pytest.fixture(autouse=True)
def update_entities(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=None)
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.update_entities", mock)
    return mock


@pytest.fixture(autouse=True)
def add_entity_insight(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock(return_value=True)
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.add_entity_insight", mock)
    return mock


def make_entity(identifier: str, entity_type: str) -> DomainEntityInfo:
    return DomainEntityInfo(
        identifier=identifier,
        creation_time=0,
        modification_time=0,
        case_identifier="1",
        alert_identifier="1",
        entity_type=entity_type,
        is_internal=False,
        is_suspicious=False,
        is_artifact=False,
        is_enriched=False,
        is_vulnerable=False,
        is_pivot=False,
        additional_properties={},
    )


def run_action(main: Callable[[], None], parameters: dict | None = None, entities: list | None = None) -> None:
    """Run an action's main() under set_metadata; call action_output.flush() between two runs."""

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=parameters or {}, entities=entities or [])
    def _run() -> None:
        main()

    _run()
