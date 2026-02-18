from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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


class GreyNoiseSDK:
    """Simple inline mock for GreyNoise SDK."""

    def __init__(self):
        """Initialize mock SDK with default responses."""
        self.quick_ip_response = None
        self.noise_response = None
        self.cve_response = None
        self.ip_multi_response = None
        self.ip_timeline_response = None

        # Failure flags
        self.should_fail_quick = False
        self.should_fail_noise = False
        self.should_fail_cve = False
        self.should_fail_ip_multi = False
        self.should_fail_ip_timeline = False
        self.should_fail_ping = False
        self.should_fail_noise_ip = False
        self.should_fail_quick_ip = False
        self.should_fail_gnql = False

        # Response data
        self.ping_response = None
        self.gnql_response = None
        self.noise_ip_response = None
        self.cve_response = None
        self.ip_timeline_response = None
        self.test_connection_response = None
        self.community_ip_response = None

    # Helper methods for setting responses
    def set_test_connection_response(self, response):
        """Set test connection response."""
        self.test_connection_response = response
        self.ping_response = response

    def set_gnql_response(self, response):
        """Set GNQL query response."""
        self.gnql_response = response

    def set_quick_ip_response(self, response):
        """Set quick IP response."""
        self.quick_ip_response = response

    def set_community_ip_response(self, response):
        """Set community IP response."""
        self.community_ip_response = response
        self.noise_ip_response = response

    def set_cve_response(self, response):
        """Set CVE response."""
        self.cve_response = response

    def set_ip_multi_response(self, response):
        """Set IP multi response for enterprise tier."""
        self.ip_multi_response = response

    def set_ip_timeline_response(self, response):
        """Set IP timeline response."""
        self.ip_timeline_response = response

    # Helper methods for simulating failures
    def simulate_test_connection_failure(self, should_fail=True):
        """Simulate test connection failure."""
        self.should_fail_ping = should_fail

    def simulate_gnql_failure(self, should_fail=True):
        """Simulate GNQL query failure."""
        self.should_fail_gnql = should_fail

    def simulate_quick_ip_failure(self, should_fail=True):
        """Simulate quick IP failure."""
        self.should_fail_quick_ip = should_fail

    def simulate_community_ip_failure(self, should_fail=True):
        """Simulate community IP failure."""
        self.should_fail_noise_ip = should_fail

    def simulate_cve_failure(self, should_fail=True):
        """Simulate CVE failure."""
        self.should_fail_cve = should_fail

    def simulate_ip_timeline_failure(self, should_fail=True):
        """Simulate IP timeline failure."""
        self.should_fail_ip_timeline = should_fail

    def ping(self):
        """Mock SDK ping method."""
        if self.should_fail_ping:
            raise ValueError("Failed to ping GreyNoise API")
        return self.ping_response or {"offering": "community", "expiration": "2024-12-31"}

    def test_connection(self):
        """Mock SDK test_connection method - alias for ping."""
        return self.ping()

    def query(
        self,
        query: str,
        size: int = 1000,
        exclude_raw: bool = True,
        quick: bool = False,
        scroll: str = None,
    ):
        """Mock SDK query method for GNQL."""
        if self.should_fail_gnql:
            raise ValueError(f"Failed GNQL query: {query}")
        return self.gnql_response or {"data": [], "count": 0, "complete": True}

    def quick(self, ip_address, include_invalid: bool = False):
        """Mock SDK quick method - supports both single IP and list of IPs."""
        if self.should_fail_quick_ip:
            raise ValueError("Failed quick check for IP(s)")

        # Handle list of IPs
        if isinstance(ip_address, list):
            if not self.quick_ip_response:
                return [
                    {"ip": ip, "noise": False, "riot": False, "classification": "unknown"}
                    for ip in ip_address
                ]
            if isinstance(self.quick_ip_response, list):
                return self.quick_ip_response
            return [self.quick_ip_response]

        # Handle single IP
        if not self.quick_ip_response:
            return {"ip": ip_address, "noise": False, "riot": False, "classification": "unknown"}
        return self.quick_ip_response

    def noise(self, ip_address: str):
        """Mock SDK noise method."""
        if self.should_fail_noise_ip:
            raise ValueError(f"Failed noise check for IP {ip_address}")
        return self.noise_ip_response or {"ip": ip_address, "noise": False, "riot": False}

    def ip(self, ip_address: str):
        """Mock SDK IP method - alias for noise."""
        return self.noise(ip_address)

    def cve(self, cve_id: str):
        """Mock SDK CVE method."""
        if self.should_fail_cve:
            raise ValueError(f"Failed CVE lookup: {cve_id}")
        return self.cve_response or {
            "cve_id": cve_id,
            "description": "Mock CVE",
            "severity": "medium",
        }

    def ip_multi(self, ip_list: list, include_invalid: bool = False):
        """Mock SDK ip_multi method for enterprise tier."""
        if self.should_fail_ip_multi:
            raise ValueError(f"Failed IP multi lookup: {ip_list}")
        return self.ip_multi_response or [
            {"ip": ip, "noise": False, "riot": False, "classification": "unknown"} for ip in ip_list
        ]

    def ip_timeline(
        self,
        ip_address: str,
        days: int = 30,
        field: str = "classification",
        granularity: str = "1d",
    ):
        """Mock SDK IP timeline method."""
        if self.should_fail_ip_timeline:
            raise ValueError(f"Failed IP timeline lookup for {ip_address}")
        return self.ip_timeline_response or {
            "ip": ip_address,
            "results": [{"timestamp": "2024-01-15T10:30:00Z", "label": "benign", "data": "10"}],
            "metadata": {"field": field, "first_seen": "2024-01-01", "granularity": granularity},
        }

    def timeline(
        self,
        ip_address: str,
        days: int = 30,
        field: str = "classification",
        granularity: str = "1d",
    ):
        """Mock SDK timeline method - alias for ip_timeline."""
        return self.ip_timeline(ip_address, days, field, granularity)

    def get_tags(self, tag_id: str):
        """Mock SDK get_tags method for GreyNoiseExtended."""
        return {
            "id": tag_id,
            "name": f"Tag {tag_id}",
            "description": f"Mock tag description for {tag_id}",
            "category": "activity",
        }


@pytest.fixture
def greynoise_sdk() -> GreyNoiseSDK:
    """Mock GreyNoise SDK for testing."""
    return GreyNoiseSDK()


@pytest.fixture(autouse=True)
def greynoise_sdk_session(monkeypatch: pytest.MonkeyPatch, greynoise_sdk: GreyNoiseSDK):
    """Mock the GreyNoise SDK and track method calls."""
    # Mock the GreyNoise SDK class to return our mock
    with patch("greynoise.GreyNoise", return_value=greynoise_sdk):
        with patch("greynoise.api.GreyNoise", return_value=greynoise_sdk):
            # Mock the GreyNoiseExtended class (which is what APIManager actually uses)
            with patch("grey_noise.core.api_manager.GreyNoiseExtended", return_value=greynoise_sdk):
                yield


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
def mock_add_entity_insight(monkeypatch: pytest.MonkeyPatch):
    """Mock the add_entity_insight method that is not provided by integration_testing framework."""
    mock_method = MagicMock(return_value=None)

    # Patch both possible import paths for SiemplifyAction
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.add_entity_insight", mock_method)
    monkeypatch.setattr("SiemplifyAction.SiemplifyAction.add_entity_insight", mock_method)


@pytest.fixture(autouse=True)
def mock_update_entities(monkeypatch: pytest.MonkeyPatch):
    """Mock the update_entities method that is not provided by integration_testing framework."""
    mock_method = MagicMock(return_value=None)

    # Patch both possible import paths for SiemplifyAction
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.update_entities", mock_method)
    monkeypatch.setattr("SiemplifyAction.SiemplifyAction.update_entities", mock_method)
