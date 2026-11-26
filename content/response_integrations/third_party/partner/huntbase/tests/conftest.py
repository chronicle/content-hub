from __future__ import annotations

# Import the SDK package before TIPCommon and integration_testing: soar_sdk registers its
# modules under their bare names (Siemplify, SiemplifyAction...) on import, and the test
# framework patches those names. Importing it first keeps one copy of every SDK class.
import soar_sdk  # noqa: F401  # isort: skip

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from huntbase.core import huntbase_manager
from huntbase.core.datamodels import HuntbaseConfig
from huntbase.core.huntbase_manager import HuntbaseManager

from .common import CONFIG
from .core.product import Huntbase
from .core.session import HuntbaseSession, SoarSdkSession

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)


class MockEntity:
    """Minimal stand-in for the SDK's DomainEntityInfo."""

    def __init__(self, identifier: str, entity_type: str, additional_properties: dict | None = None) -> None:
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = dict(additional_properties or {})
        self.is_enriched = False
        self.is_internal = False
        self.is_suspicious = False
        self.is_artifact = False
        self.is_vulnerable = False
        self.is_pivot = False

    def _update_internal_properties(self) -> None:
        pass

    def to_dict(self) -> SingleJson:
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
            "is_enriched": self.is_enriched,
            "is_suspicious": self.is_suspicious,
        }


@pytest.fixture(name="huntbase")
def huntbase_product() -> Huntbase:
    return Huntbase()


@pytest.fixture(name="script_session")
def huntbase_script_session(monkeypatch: pytest.MonkeyPatch, huntbase: Huntbase) -> HuntbaseSession:
    session: HuntbaseSession = HuntbaseSession(huntbase)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    return session


@pytest.fixture(name="sdk_session")
def soar_sdk_session(monkeypatch: pytest.MonkeyPatch) -> SoarSdkSession:
    """SDK calls to the SOAR platform; answers case metadata for tests that set a case id."""
    session = SoarSdkSession()
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record retry waits instead of sleeping."""
    waits: list[float] = []
    monkeypatch.setattr(huntbase_manager, "_sleep", waits.append)
    return waits


@pytest.fixture(name="manager")
def huntbase_manager_fixture(script_session: HuntbaseSession) -> HuntbaseManager:
    config = HuntbaseConfig(api_root=CONFIG["API Root"], api_key=CONFIG["API Key"])
    return HuntbaseManager(config, logger=Logger(), session=script_session)


@pytest.fixture(name="entity_calls")
def mock_entity_calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """The integration_testing framework does not provide these SDK calls."""
    calls = {
        "update_entities": MagicMock(return_value=None),
        "add_entity_insight": MagicMock(return_value=None),
        "create_case_insight": MagicMock(return_value=None),
    }
    for name, mock in calls.items():
        monkeypatch.setattr(f"soar_sdk.SiemplifyAction.SiemplifyAction.{name}", mock)
    return calls
