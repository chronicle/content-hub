from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

pytest_plugins = ("integration_testing.conftest",)


class MockEntity:
    """Simple mock entity class that mimics DomainEntityInfo."""

    def __init__(self, identifier: str, entity_type: str, additional_properties: dict):
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = additional_properties
        self.is_enriched = False
        self.is_internal = False
        self.is_suspicious = False
        self.is_artifact = False
        self.is_vulnerable = False
        self.is_pivot = False

    def _update_internal_properties(self):
        """Mock method to satisfy SOAR framework requirements."""
        pass

    def to_dict(self):
        """Convert entity to dictionary for JSON serialization."""
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
            "is_enriched": self.is_enriched,
            "is_internal": self.is_internal,
            "is_suspicious": self.is_suspicious,
            "is_artifact": self.is_artifact,
            "is_vulnerable": self.is_vulnerable,
            "is_pivot": self.is_pivot,
        }


@pytest.fixture
def cyware() -> CywareIntelExchange:
    return CywareIntelExchange()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    cyware: CywareIntelExchange,
) -> CywareSession:
    session: CywareSession = CywareSession(cyware)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(requests, "session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
        monkeypatch.setattr("requests.session", lambda: session)
        monkeypatch.setattr(requests, "post", session.post)
        monkeypatch.setattr(requests, "get", session.get)

    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, cyware: CywareIntelExchange) -> CywareSession:
    session: CywareSession = CywareSession(cyware)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session


@pytest.fixture(autouse=True)
def convert_entities(monkeypatch: pytest.MonkeyPatch):
    """Automatically convert dictionary entities to proper entity objects."""
    import integration_testing.set_meta as set_meta_module

    # Store the original functions
    original_get_entities = set_meta_module._get_entities_path_and_fn
    original_get_entities_2 = set_meta_module._get_entities_path_and_fn_2

    def _convert_dict_to_entity(entity_dict: dict[str, Any]) -> MockEntity:
        """Convert a dictionary to a mock entity object with proper attributes."""
        return MockEntity(
            identifier=entity_dict.get("identifier", ""),
            entity_type=entity_dict.get("entity_type", ""),
            additional_properties=dict(entity_dict.get("additional_properties", {})),
        )

    def _get_entities_path_and_fn_patched(entities):
        """Patched version that converts dict entities to proper objects."""
        if entities and isinstance(entities, list) and len(entities) > 0:
            if isinstance(entities[0], dict):
                entities = [_convert_dict_to_entity(e) for e in entities]
        return original_get_entities(entities)

    def _get_entities_path_and_fn_2_patched(entities):
        """Patched version that converts dict entities to proper objects."""
        if entities and isinstance(entities, list) and len(entities) > 0:
            if isinstance(entities[0], dict):
                entities = [_convert_dict_to_entity(e) for e in entities]
        return original_get_entities_2(entities)

    # Patch both entity functions
    monkeypatch.setattr(
        set_meta_module, "_get_entities_path_and_fn", _get_entities_path_and_fn_patched
    )
    monkeypatch.setattr(
        set_meta_module, "_get_entities_path_and_fn_2", _get_entities_path_and_fn_2_patched
    )


@pytest.fixture(autouse=True)
def mock_update_entities(monkeypatch: pytest.MonkeyPatch):
    """Mock the update_entities method that is not provided by integration_testing framework."""
    mock_method = MagicMock(return_value=None)

    # Patch both possible import paths for SiemplifyAction
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.update_entities", mock_method)
    monkeypatch.setattr("SiemplifyAction.SiemplifyAction.update_entities", mock_method)
