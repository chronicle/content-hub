from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock

import pytest
import requests

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


class MockResponse:
    """Mock HTTP response."""

    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error", response=self)


class CensysAPIManager:
    """Mock Censys API Manager for testing."""

    def __init__(self):
        """Initialize mock API Manager with default responses."""
        # Response data
        self.connectivity_response = None
        self.enrich_hosts_response = None
        self.enrich_web_properties_response = None
        self.enrich_certificates_response = None
        self.host_history_response = None
        self.value_counts_response = None
        self.search_query_response = None
        self.initiate_rescan_response = None
        self.rescan_status_response = None

        # Failure flags
        self.should_fail_connectivity = False
        self.should_fail_enrich_hosts = False
        self.should_fail_enrich_web_properties = False
        self.should_fail_enrich_certificates = False
        self.should_fail_host_history = False
        self.should_fail_value_counts = False
        self.should_fail_search_query = False
        self.should_fail_initiate_rescan = False
        self.should_fail_rescan_status = False

        # Exception types to raise
        self.exception_type = None
        self.exception_message = "API Error"

    # Helper methods for setting responses
    def set_connectivity_response(self, response: dict):
        """Set test connectivity response."""
        self.connectivity_response = response

    def set_enrich_hosts_response(self, response: dict):
        """Set enrich hosts response."""
        self.enrich_hosts_response = response

    def set_enrich_web_properties_response(self, response: dict):
        """Set enrich web properties response."""
        self.enrich_web_properties_response = response

    def set_enrich_certificates_response(self, response: dict):
        """Set enrich certificates response."""
        self.enrich_certificates_response = response

    def set_host_history_response(self, response: dict):
        """Set host history response."""
        self.host_history_response = response

    def set_value_counts_response(self, response: dict):
        """Set value counts response."""
        self.value_counts_response = response

    def set_search_query_response(self, response: dict):
        """Set search query response."""
        self.search_query_response = response

    def set_initiate_rescan_response(self, response: dict):
        """Set initiate rescan response."""
        self.initiate_rescan_response = response

    def set_rescan_status_response(self, response: dict):
        """Set rescan status response."""
        self.rescan_status_response = response

    # Helper methods for simulating failures
    def simulate_connectivity_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate connectivity failure."""
        self.should_fail_connectivity = should_fail
        self.exception_type = exception_type

    def simulate_enrich_hosts_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate enrich hosts failure."""
        self.should_fail_enrich_hosts = should_fail
        self.exception_type = exception_type

    def simulate_enrich_web_properties_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate enrich web properties failure."""
        self.should_fail_enrich_web_properties = should_fail
        self.exception_type = exception_type

    def simulate_enrich_certificates_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate enrich certificates failure."""
        self.should_fail_enrich_certificates = should_fail
        self.exception_type = exception_type

    def simulate_host_history_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate host history failure."""
        self.should_fail_host_history = should_fail
        self.exception_type = exception_type

    def simulate_initiate_rescan_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate initiate rescan failure."""
        self.should_fail_initiate_rescan = should_fail
        self.exception_type = exception_type

    def simulate_rescan_status_failure(
        self, should_fail: bool = True, exception_type: str = "generic"
    ):
        """Simulate rescan status failure."""
        self.should_fail_rescan_status = should_fail
        self.exception_type = exception_type

    def _raise_exception(self):
        """Raise appropriate exception based on exception_type."""
        import os
        import sys

        # Add parent directory to path to import from censys module
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from core.censys_exceptions import (
            CensysException,
            RateLimitException,
            UnauthorizedErrorException,
            ValidationException,
        )

        if self.exception_type == "unauthorized":
            raise UnauthorizedErrorException(
                "Unauthorized, please verify your API Key and Organization ID."
            )
        elif self.exception_type == "rate_limit":
            raise RateLimitException("API rate limit exceeded")
        elif self.exception_type == "validation":
            raise ValidationException("Validation error: Invalid input parameters")
        elif self.exception_type == "http_error":
            response = MagicMock()
            response.status_code = 500
            raise requests.HTTPError("500 Server Error", response=response)
        else:
            raise CensysException(self.exception_message)

    # Mock API methods
    def test_connectivity(self) -> bool:
        """Mock test_connectivity method."""
        if self.should_fail_connectivity:
            self._raise_exception()
        return self.connectivity_response if self.connectivity_response is not None else True

    def enrich_hosts(self, host_ids: list, at_time: Optional[str] = None) -> dict:
        """Mock enrich_hosts method."""
        if self.should_fail_enrich_hosts:
            self._raise_exception()
        return self.enrich_hosts_response or {"result": []}

    def enrich_web_properties(self, webproperty_ids: list, at_time: Optional[str] = None) -> dict:
        """Mock enrich_web_properties method."""
        if self.should_fail_enrich_web_properties:
            self._raise_exception()
        return self.enrich_web_properties_response or {"result": []}

    def enrich_certificates(self, certificate_ids: list) -> dict:
        """Mock enrich_certificates method."""
        if self.should_fail_enrich_certificates:
            self._raise_exception()
        return self.enrich_certificates_response or {"result": []}

    def get_host_history(self, host_id: str, start_time: str, end_time: str) -> dict:
        """Mock get_host_history method."""
        if self.should_fail_host_history:
            self._raise_exception()
        return self.host_history_response or {"result": {"events": [], "total_events": 0}}

    def get_value_counts(self, query: Optional[str], and_count_conditions: list) -> dict:
        """Mock get_value_counts method."""
        if self.should_fail_value_counts:
            self._raise_exception()
        return self.value_counts_response or {"result": {"value_counts": []}}

    def run_search_query_with_pagination(
        self, query: str, max_pages: int = 10, max_records: Optional[int] = None
    ) -> dict:
        """Mock run_search_query_with_pagination method."""
        if self.should_fail_search_query:
            self._raise_exception()
        return self.search_query_response or {"result": {"hits": [], "total_available": 0}}

    def initiate_rescan(
        self,
        ioc_type: str,
        ioc_value: str,
        port: int,
        protocol: Optional[str] = None,
        transport_protocol: Optional[str] = None,
    ) -> dict:
        """Mock initiate_rescan method."""
        if self.should_fail_initiate_rescan:
            self._raise_exception()
        return self.initiate_rescan_response or {"result": {"scan_id": "mock_scan_id"}}

    def get_rescan_status(self, scan_id: str) -> dict:
        """Mock get_rescan_status method."""
        if self.should_fail_rescan_status:
            self._raise_exception()
        return self.rescan_status_response or {"result": {"status": "completed"}}


@pytest.fixture
def censys_manager() -> CensysAPIManager:
    """Mock Censys API Manager for testing."""
    return CensysAPIManager()


@pytest.fixture(autouse=True)
def mock_requests_session(monkeypatch: pytest.MonkeyPatch, censys_manager: CensysAPIManager):
    """Mock requests.Session to intercept HTTP calls."""

    class MockSession:
        def __init__(self):
            self.headers = {}

        def update(self, *args, **kwargs):
            pass

        def request(self, method, url, **kwargs):
            # Check for failure flags and raise exceptions if needed
            if "/accounts/organizations/" in url and censys_manager.should_fail_connectivity:
                censys_manager._raise_exception()
            elif (
                "/asset/host" in url
                and method == "POST"
                and censys_manager.should_fail_enrich_hosts
            ):
                censys_manager._raise_exception()
            elif "/asset/webproperty" in url and censys_manager.should_fail_enrich_web_properties:
                censys_manager._raise_exception()
            elif "/asset/certificate" in url and censys_manager.should_fail_enrich_certificates:
                censys_manager._raise_exception()
            elif "/timeline" in url and censys_manager.should_fail_host_history:
                censys_manager._raise_exception()
            elif "/scans/rescan" in url and censys_manager.should_fail_initiate_rescan:
                censys_manager._raise_exception()
            elif "/scans/" in url and method == "GET" and censys_manager.should_fail_rescan_status:
                censys_manager._raise_exception()

            # Return mock responses
            if "/accounts/organizations/" in url:
                return MockResponse(
                    censys_manager.connectivity_response or {"result": {"id": "test_org"}},
                    200,
                )
            elif "/asset/host" in url and method == "POST":
                return MockResponse(censys_manager.enrich_hosts_response or {"result": []}, 200)
            elif "/asset/webproperty" in url:
                return MockResponse(
                    censys_manager.enrich_web_properties_response or {"result": []},
                    200,
                )
            elif "/asset/certificate" in url:
                return MockResponse(
                    censys_manager.enrich_certificates_response or {"result": []},
                    200,
                )
            elif "/timeline" in url:
                return MockResponse(
                    censys_manager.host_history_response or {"result": {"events": []}},
                    200,
                )
            elif "/scans/rescan" in url:
                return MockResponse(
                    censys_manager.initiate_rescan_response or {"result": {"scan_id": "test"}},
                    200,
                )
            elif "/scans/" in url:
                return MockResponse(
                    censys_manager.rescan_status_response or {"result": {"status": "completed"}},
                    200,
                )
            else:
                return MockResponse({}, 200)

    # Mock requests.Session to return our MockSession
    monkeypatch.setattr(requests, "Session", MockSession)
    yield


@pytest.fixture(autouse=True)
def convert_entities(monkeypatch: pytest.MonkeyPatch):
    """Automatically convert dictionary entities to proper entity objects."""
    import integration_testing.set_meta as set_meta_module

    # Store the original functions
    original_get_entities = set_meta_module._get_entities_path_and_fn
    original_get_entities_2 = set_meta_module._get_entities_path_and_fn_2

    def _convert_dict_to_entity(entity_dict: dict) -> MockEntity:
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
        set_meta_module,
        "_get_entities_path_and_fn",
        _get_entities_path_and_fn_patched,
    )
    monkeypatch.setattr(
        set_meta_module,
        "_get_entities_path_and_fn_2",
        _get_entities_path_and_fn_2_patched,
    )


@pytest.fixture(autouse=True)
def mock_siemplify_methods(monkeypatch: pytest.MonkeyPatch):
    """Mock Siemplify methods that are not provided by integration_testing framework."""
    # Mock update_entities
    mock_update = MagicMock(return_value=None)
    monkeypatch.setattr("soar_sdk.SiemplifyAction.SiemplifyAction.update_entities", mock_update)

    # Mock get_system_version to prevent API calls during APIManager initialization
    mock_version = MagicMock(return_value="1.0.0")
    monkeypatch.setattr(
        "soar_sdk.SiemplifyAction.SiemplifyAction.get_system_version",
        mock_version,
    )
