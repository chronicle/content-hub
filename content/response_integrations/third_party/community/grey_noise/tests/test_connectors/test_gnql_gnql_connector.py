from __future__ import annotations

import importlib.util
import pathlib
from types import ModuleType
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from grey_noise.core.datamodels import GNQLEventResult

CONNECTOR_FILE = (
    pathlib
    .Path(__file__)
    .parents[2]
    .joinpath("connectors", "grey_noise_pull_indicators_via_gnql_connector.py")
)


def _load_connector_module() -> ModuleType:
    """
    Dynamically load the GNQL connector script as a regular Python module.

    The connector file name contains spaces, so we cannot import it using the
    normal dotted module syntax. This helper loads it from its file path and
    registers it under a stable module name so we can patch its attributes.
    """
    module_name = "grey_noise.connectors.gnql_connector"

    # Reuse already loaded module if present
    existing = importlib.util.find_spec(module_name)
    if existing and module_name in globals():
        return globals()[module_name]  # type: ignore[return-value]

    spec = importlib.util.spec_from_file_location(module_name, CONNECTOR_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load connector module from {CONNECTOR_FILE}")

    module = importlib.util.module_from_spec(spec)
    # Register module so relative imports inside the connector keep working
    import sys

    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


@pytest.fixture
def connector_module(monkeypatch: pytest.MonkeyPatch):
    """
    Load the connector module and patch its external dependencies with simple fakes.

    This keeps the tests focused on the connector control‑flow and parameter
    handling rather than on real SOAR or GreyNoise SDK behaviour.
    """
    module = _load_connector_module()

    # ------------------------------------------------------------------
    # Patch Siemplify connector execution environment
    # ------------------------------------------------------------------
    class FakeLogger:
        def __init__(self):
            self.info = MagicMock()
            self.error = MagicMock()
            self.exception = MagicMock()

    class FakeSiemplifyConnector:
        def __init__(self):
            self.LOGGER = FakeLogger()
            self.script_name = ""
            self._returned_package: List[Any] | None = None

        def return_package(self, alerts: List[Any]):
            self._returned_package = alerts

    fake_siemplify = FakeSiemplifyConnector()

    class FakeSiemplifyConnectorExecution:
        def __call__(self):
            return fake_siemplify

        def __init__(self, *_, **__):
            pass

        def __new__(cls, *_, **__):  # pragma: no cover - construction detail
            return fake_siemplify

    monkeypatch.setattr(module, "SiemplifyConnectorExecution", FakeSiemplifyConnectorExecution)

    # ------------------------------------------------------------------
    # Patch helper functions and external utilities
    # ------------------------------------------------------------------
    extractor_values: dict[str, Any] = {}

    def _extract_connector_param(
        siemplify: Any,
        param_name: str,
        input_type: type | None = None,
        default_value: Any | None = None,
        is_mandatory: bool | None = None,
        print_value: bool | None = None,
    ):
        value = extractor_values.get(param_name, default_value)
        return value

    monkeypatch.setattr(module, "extract_connector_param", _extract_connector_param)

    # Validate integer using real implementation from core.utils
    # (already imported inside connector as validate_integer_param)

    # read/write ids
    existing_ids_store: list[str] = []

    def _read_ids(siemplify: Any) -> list[str]:
        return list(existing_ids_store)

    def _write_ids(siemplify: Any, ids: list[str]) -> None:
        existing_ids_store.clear()
        existing_ids_store.extend(ids)

    monkeypatch.setattr(module, "read_ids", _read_ids)
    monkeypatch.setattr(module, "write_ids", _write_ids)

    # Overflow / timeout helpers
    monkeypatch.setattr(module, "is_overflowed", lambda *_, **__: False)
    monkeypatch.setattr(module, "is_approaching_timeout", lambda *_, **__: False)

    # Environment factory
    class FakeEnvironmentManager:
        def get_environment(self, *_: Any, **__: Any) -> str:
            return "TEST_ENV"

    class FakeEnvironmentFactory:
        @staticmethod
        def create_environment_manager(*_: Any, **__: Any) -> FakeEnvironmentManager:
            return FakeEnvironmentManager()

    monkeypatch.setattr(module, "GetEnvironmentCommonFactory", FakeEnvironmentFactory)

    # AlertInfo data model
    class FakeAlertInfo:
        def __init__(self):
            # Minimal set of attributes used by the connector logic
            self.ticket_id = None
            self.rule_generator = "rule"
            self.environment = "env"
            self.device_product = "product"

    monkeypatch.setattr(module, "AlertInfo", FakeAlertInfo)

    # APIManager – return pre‑built GNQL events
    class FakeAPIManager:
        def __init__(self, api_key: str, siemplify: Any):
            self.api_key = api_key
            self.siemplify = siemplify
            self._events: list[Any] = []

        def set_events(self, events: list[Any]):
            self._events = events

        def get_gnql_events(
            self,
            query: str,
            page_size: int,
            existing_ids: list[str],
            connector_start_time: int,
            timeout: int,
            max_results: int,
        ) -> list[Any]:
            return self._events

    fake_manager = FakeAPIManager("dummy", fake_siemplify)
    fake_events: list[Any] = []

    def _api_manager_factory(api_key: str, siemplify: Any):
        # Allow tests to control returned events through fake_events list
        fake_manager.api_key = api_key
        fake_manager.siemplify = siemplify
        fake_manager._events = list(fake_events)
        return fake_manager

    monkeypatch.setattr(module, "APIManager", _api_manager_factory)

    # Expose knobs for individual tests
    module._test_helpers = {
        "siemplify": fake_siemplify,
        "extractor_values": extractor_values,
        "existing_ids_store": existing_ids_store,
        "fake_events": fake_events,
    }

    return module


class TestGNQLConnector:
    """Connector‑level tests for the GreyNoise GNQL connector."""

    def test_main_success_creates_alerts_and_saves_ids(self, connector_module: ModuleType) -> None:
        """Happy‑path run: connector executes GNQL flow without raising exceptions."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]

        # Connector parameters
        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # One real GNQL event which will produce one AlertInfo
        fake_events.clear()
        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        # Execute connector (not in test mode, so IDs should be written)
        connector_module.main(is_test_run=False)

        # Verify a single alert was returned
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 1

        # Verify deduplication IDs were persisted
        existing_ids_store = helpers["existing_ids_store"]
        assert len(existing_ids_store) == 1
        assert existing_ids_store[0] == alerts[0].ticket_id

    def test_main_uses_default_query_when_missing(self, connector_module: ModuleType) -> None:
        """If 'Query' parameter is empty, the connector should fall back to default GNQL."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]

        extractor_values.clear()
        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "   ",  # whitespace only
            "Size": "",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Provide empty events to keep the run trivial
        fake_events.clear()

        connector_module.main(is_test_run=False)

        # Ensure the run completes without raising – behaviour of default query
        # itself is exercised by APIManager tests; here we only care that main
        # does not fail when the query is empty.

    def test_main_raises_on_rate_limit_in_test_mode(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When RateLimitError occurs in test mode, it should be re‑raised."""
        from greynoise.exceptions import RateLimitError

        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]

        extractor_values.clear()
        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Make APIManager.get_gnql_events raise RateLimitError
        def _failing_get_gnql_events(*_, **__):
            raise RateLimitError("Rate limit exceeded")

        monkeypatch.setattr(
            connector_module,
            "APIManager",
            lambda *_, **__: MagicMock(get_gnql_events=_failing_get_gnql_events),
        )

        with pytest.raises(RateLimitError):
            connector_module.main(is_test_run=True)

    def test_main_handles_timeout_during_event_processing(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test timeout handling during GNQL event processing."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]
        siemplify = helpers["siemplify"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Add a fake event
        fake_events.clear()
        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        # Mock is_approaching_timeout to return True to trigger timeout handling
        timeout_called = False

        def mock_timeout(*args, **kwargs):
            nonlocal timeout_called
            timeout_called = True
            return True

        monkeypatch.setattr(connector_module, "is_approaching_timeout", mock_timeout)

        # Should complete without raising, but with timeout handling triggered
        connector_module.main(is_test_run=False)

        # Verify timeout was checked (though no alerts should be returned due to timeout)
        assert timeout_called

        # Verify no alerts were returned due to timeout
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 0

    def test_main_handles_overflow_during_event_processing(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test overflow handling during GNQL event processing."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]
        siemplify = helpers["siemplify"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Add a fake event
        fake_events.clear()
        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        # Mock is_overflowed to return True to trigger overflow handling
        overflow_called = False

        def mock_overflow(*args, **kwargs):
            nonlocal overflow_called
            overflow_called = True
            return True

        monkeypatch.setattr(connector_module, "is_overflowed", mock_overflow)

        # Should complete without raising, but with overflow handling triggered
        connector_module.main(is_test_run=False)

        # Verify overflow was checked
        assert overflow_called

        # Verify no alerts were returned due to overflow
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 0

    def test_main_handles_event_processing_exception(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test exception handling during individual event processing."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Add a fake event
        fake_events.clear()
        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        # Mock GNQLEventResult.get_alert_info to raise an exception
        def mock_get_alert_info(*args, **kwargs):
            raise ValueError("Test exception in event processing")

        monkeypatch.setattr(GNQLEventResult, "get_alert_info", mock_get_alert_info)

        # Should complete without raising (exceptions in event processing are caught)
        connector_module.main(is_test_run=False)

        # Verify no alerts were returned due to exception
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 0

    def test_main_handles_request_failure_401_error(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test RequestFailure handling with 401 authentication error."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        from greynoise.exceptions import RequestFailure

        # Create a fake APIManager class that raises RequestFailure
        class FakeAPIManager:
            def __init__(self, api_key, siemplify):
                self.api_key = api_key
                self.siemplify = siemplify

            def get_gnql_events(self, *args, **kwargs):
                raise RequestFailure("401 Client Error: Unauthorized")

        monkeypatch.setattr(connector_module, "APIManager", FakeAPIManager)

        # Should complete without raising (RequestFailure is caught)
        connector_module.main(is_test_run=False)

        # Verify no package was returned due to error (exceptions don't call return_package)
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is None

    def test_main_handles_request_failure_non_401_error(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test RequestFailure handling with non-401 errors."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        from greynoise.exceptions import RequestFailure

        # Create a fake APIManager class that raises RequestFailure with non-401 error
        class FakeAPIManager:
            def __init__(self, api_key, siemplify):
                self.api_key = api_key
                self.siemplify = siemplify

            def get_gnql_events(self, *args, **kwargs):
                raise RequestFailure("500 Internal Server Error")

        monkeypatch.setattr(connector_module, "APIManager", FakeAPIManager)

        # Should complete without raising (RequestFailure is caught)
        connector_module.main(is_test_run=False)

        # Verify no package was returned due to error
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is None

    def test_main_handles_rate_limit_error_in_non_test_mode(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test RateLimitError handling in non-test mode."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        from greynoise.exceptions import RateLimitError

        # Create a fake APIManager class that raises RateLimitError
        class FakeAPIManager:
            def __init__(self, api_key, siemplify):
                self.api_key = api_key
                self.siemplify = siemplify

            def get_gnql_events(self, *args, **kwargs):
                raise RateLimitError("Rate limit exceeded")

        monkeypatch.setattr(connector_module, "APIManager", FakeAPIManager)

        # Should complete without raising (RateLimitError is caught in non-test mode)
        connector_module.main(is_test_run=False)

        # Verify no package was returned due to error
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is None

    def test_main_handles_empty_events_list(self, connector_module: ModuleType) -> None:
        """Test handling when no GNQL events are returned."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]
        siemplify = helpers["siemplify"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # No events returned
        fake_events.clear()

        # Should complete successfully with empty alerts list
        connector_module.main(is_test_run=False)

        # Verify empty alerts list was returned
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 0

    def test_main_handles_multiple_events_with_deduplication(
        self, connector_module: ModuleType
    ) -> None:
        """Test processing multiple events (deduplication happens in APIManager)."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]
        siemplify = helpers["siemplify"]
        existing_ids_store = helpers["existing_ids_store"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Add multiple unique events (APIManager handles deduplication)
        fake_events.clear()

        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        fake_events.append(
            GNQLEventResult({
                "ip": "5.6.7.8",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-02",
                    "first_seen": "2023-12-02",
                    "last_seen_timestamp": "2024-01-02T12:00:00Z",
                },
            })
        )

        fake_events.append(
            GNQLEventResult({
                "ip": "9.10.11.12",
                "internet_scanner_intelligence": {
                    "classification": "suspicious",
                    "last_seen": "2024-01-03",
                    "first_seen": "2023-12-03",
                    "last_seen_timestamp": "2024-01-03T12:00:00Z",
                },
            })
        )

        # Should complete successfully, processing all events
        connector_module.main(is_test_run=False)

        # Verify all events were processed
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 3  # All three unique events processed

        # Verify all event IDs were persisted
        expected_ids = [
            "1.2.3.4_2024-01-01T12:00:00Z",
            "5.6.7.8_2024-01-02T12:00:00Z",
            "9.10.11.12_2024-01-03T12:00:00Z",
        ]
        for expected_id in expected_ids:
            assert expected_id in existing_ids_store

    def test_main_handles_generic_exception_in_non_test_mode(
        self, connector_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test generic exception handling in non-test mode."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": "10",
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Create a fake APIManager class that raises a generic exception
        class FakeAPIManager:
            def __init__(self, api_key, siemplify):
                self.api_key = api_key
                self.siemplify = siemplify

            def get_gnql_events(self, *args, **kwargs):
                raise ConnectionError("Network connection failed")

        monkeypatch.setattr(connector_module, "APIManager", FakeAPIManager)

        # Should complete without raising (generic exception is caught in non-test mode)
        connector_module.main(is_test_run=False)

        # Verify no package was returned due to error
        siemplify = helpers["siemplify"]
        alerts = siemplify._returned_package
        assert alerts is None

    def test_main_skips_id_persistence_in_test_mode(self, connector_module: ModuleType) -> None:
        """Test that IDs are not persisted in test mode even when alerts are created."""
        helpers = connector_module._test_helpers
        extractor_values = helpers["extractor_values"]
        fake_events: list[Any] = helpers["fake_events"]
        siemplify = helpers["siemplify"]
        existing_ids_store = helpers["existing_ids_store"]

        # Clear any existing IDs
        existing_ids_store.clear()

        extractor_values.update({
            "GN API Key": "api-key",
            "Query": "classification:malicious",
            "Size": str(1),  # Test mode will override to TEST_MODE_MAX_RESULTS
            "Environment Field Name": "",
            "Environment Regex Pattern": "",
            "PythonProcessTimeout": 300,
            "DeviceProductField": "DeviceProduct",
        })

        # Add one event
        fake_events.clear()
        fake_events.append(
            GNQLEventResult({
                "ip": "1.2.3.4",
                "internet_scanner_intelligence": {
                    "classification": "malicious",
                    "last_seen": "2024-01-01",
                    "first_seen": "2023-12-01",
                    "last_seen_timestamp": "2024-01-01T12:00:00Z",
                },
            })
        )

        # Run in test mode
        connector_module.main(is_test_run=True)

        # Verify alert was created
        alerts = siemplify._returned_package
        assert alerts is not None
        assert len(alerts) == 1

        # Verify IDs were NOT persisted (should still be empty)
        assert len(existing_ids_store) == 0
