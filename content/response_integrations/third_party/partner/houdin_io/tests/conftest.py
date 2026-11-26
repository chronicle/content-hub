from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import requests
from integration_testing.set_meta import set_metadata
from soar_sdk.SiemplifyDataModel import DomainEntityInfo

from .common import CONFIG_PATH
from .mock_session import HoudinSession

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)

# TIPCommon builds the action from the flat `SiemplifyAction` module, the SDK namespace
# exposes the same file as `soar_sdk.SiemplifyAction`; a patch must land on both classes.
SDK_ACTION_CLASSES: tuple[str, ...] = ("SiemplifyAction.SiemplifyAction", "soar_sdk.SiemplifyAction.SiemplifyAction")


def patch_sdk_method(monkeypatch: pytest.MonkeyPatch, method: str, mock: MagicMock) -> None:
    for class_path in SDK_ACTION_CLASSES:
        monkeypatch.setattr(f"{class_path}.{method}", mock)


@pytest.fixture(autouse=True)
def houdin(monkeypatch: pytest.MonkeyPatch) -> HoudinSession:
    """Every requests.Session the manager opens is the mocked Houdin."""
    session: HoudinSession = HoudinSession()
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.setattr(requests, "session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def update_entities(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock: MagicMock = MagicMock(return_value=None)
    patch_sdk_method(monkeypatch, "update_entities", mock)
    return mock


@pytest.fixture(autouse=True)
def add_entity_insight(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock: MagicMock = MagicMock(return_value=True)
    patch_sdk_method(monkeypatch, "add_entity_insight", mock)
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


def run_action(
    main: Callable[[], None],
    parameters: SingleJson | None = None,
    entities: list[DomainEntityInfo] | None = None,
) -> None:
    """Run an action's main() under set_metadata; call action_output.flush() between two runs."""

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=parameters or {}, entities=entities or [])
    def _run() -> None:
        main()

    _run()
