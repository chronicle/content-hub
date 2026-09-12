from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest_plugins = ("integration_testing.conftest",)


class MockEntity:
    """Simple mock entity class that mimics DomainEntityInfo."""

    def __init__(self, identifier: str, entity_type: str, additional_properties: dict | None = None):
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = additional_properties or {}
        self.is_enriched = False
        self.is_internal = False
        self.is_suspicious = False
        self.is_artifact = False
        self.is_vulnerable = False
        self.is_pivot = False

    def _update_internal_properties(self):
        pass

    def to_dict(self):
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
            "is_enriched": self.is_enriched,
            "is_suspicious": self.is_suspicious,
        }


class MockDomainToolsManager:
    """Mock DomainToolsManager for testing actions without real API calls."""

    def __init__(self):
        self.enrich_domains_response = []
        self.investigate_domains_response = []
        self.parsed_domain_rdap_response = None
        self.whois_history_response = None

        self.should_fail_enrich = False
        self.should_fail_investigate = False
        self.should_fail_rdap = False
        self.should_fail_whois = False
        self.exception_message = "API Error"

    def set_enrich_domains_response(self, response):
        self.enrich_domains_response = response

    def set_investigate_domains_response(self, response):
        self.investigate_domains_response = response

    def set_parsed_domain_rdap_response(self, response):
        self.parsed_domain_rdap_response = response

    def set_whois_history_response(self, response):
        self.whois_history_response = response

    def simulate_enrich_failure(self, should_fail: bool = True):
        self.should_fail_enrich = should_fail

    def simulate_investigate_failure(self, should_fail: bool = True):
        self.should_fail_investigate = should_fail

    def enrich_domains_with_risk(self, domains: list):
        if self.should_fail_enrich:
            raise Exception(self.exception_message)
        return self.enrich_domains_response

    def investigate_domains(self, domains: list):
        if self.should_fail_investigate:
            raise Exception(self.exception_message)
        return self.investigate_domains_response

    def get_parsed_domain_rdap(self, domain: str):
        if self.should_fail_rdap:
            raise Exception(self.exception_message)
        return self.parsed_domain_rdap_response

    def get_whois_history(self, domain: str):
        if self.should_fail_whois:
            raise Exception(self.exception_message)
        return self.whois_history_response


@pytest.fixture
def dt_manager() -> MockDomainToolsManager:
    return MockDomainToolsManager()


@pytest.fixture(autouse=True)
def mock_dt_manager(monkeypatch: pytest.MonkeyPatch, dt_manager: MockDomainToolsManager):
    """Patch DomainToolsManager in all action modules."""
    monkeypatch.setattr(
        "domain_tools.actions.EnrichDomainRisk.DomainToolsManager",
        lambda **kwargs: dt_manager,
    )
    monkeypatch.setattr(
        "domain_tools.actions.BulkEnrichDomains.DomainToolsManager",
        lambda **kwargs: dt_manager,
    )
    monkeypatch.setattr(
        "domain_tools.actions.GetDomainProfile.DomainToolsManager",
        lambda **kwargs: dt_manager,
    )
    monkeypatch.setattr(
        "domain_tools.actions.Ping.DomainToolsManager",
        lambda **kwargs: dt_manager,
    )


@pytest.fixture(autouse=True)
def mock_siemplify_methods(monkeypatch: pytest.MonkeyPatch):
    """Mock SOAR SDK methods not provided by integration_testing."""
    monkeypatch.setattr(
        "soar_sdk.SiemplifyAction.SiemplifyAction.update_entities",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        "soar_sdk.SiemplifyAction.SiemplifyAction.get_system_version",
        MagicMock(return_value="1.0.0"),
    )


@pytest.fixture(autouse=True)
def convert_entities(monkeypatch: pytest.MonkeyPatch):
    """Convert dict entities passed to @set_metadata into MockEntity objects."""
    import integration_testing.set_meta as set_meta_module

    original_get_entities = set_meta_module._get_entities_path_and_fn
    original_get_entities_2 = set_meta_module._get_entities_path_and_fn_2

    def _to_entity(entity_dict: dict) -> MockEntity:
        return MockEntity(
            identifier=entity_dict.get("identifier", ""),
            entity_type=entity_dict.get("entity_type", ""),
            additional_properties=dict(entity_dict.get("additional_properties", {})),
        )

    def patched(entities):
        if entities and isinstance(entities, list) and isinstance(entities[0], dict):
            entities = [_to_entity(e) for e in entities]
        return original_get_entities(entities)

    def patched_2(entities):
        if entities and isinstance(entities, list) and isinstance(entities[0], dict):
            entities = [_to_entity(e) for e in entities]
        return original_get_entities_2(entities)

    monkeypatch.setattr(set_meta_module, "_get_entities_path_and_fn", patched)
    monkeypatch.setattr(set_meta_module, "_get_entities_path_and_fn_2", patched_2)
