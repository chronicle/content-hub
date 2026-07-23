from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Any, List

import pytest

CONNECTOR_FILE = (
    pathlib
    .Path(__file__)
    .parents[2]
    .joinpath("connectors", "generate_alert_from_rubrik_classification_events.py")
)

RESULTS_MESSAGE = "Results available in the Objects page for the workload"


def _load_connector_module() -> ModuleType:
    """Load the connector script as a module.

    The connector uses package-relative imports (``from ..core ...``), so it is
    registered under the integration's real package path
    ``rubrik_security_cloud.connectors.<name>`` to keep those imports working.
    """
    module_name = "rubrik_security_cloud.connectors.classification_events_connector"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, CONNECTOR_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load connector module from {CONNECTOR_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


class _FakeLogger:
    def info(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


class _FakeSiemplify:
    def __init__(self) -> None:
        self.LOGGER = _FakeLogger()
        self.script_name = ""
        self.run_folder = None
        self.returned_package: List[Any] | None = None

    def return_package(self, package: List[Any]) -> None:
        self.returned_package = package


class _FakeEnvManager:
    def get_environment(self, *_: Any, **__: Any) -> str:
        return "Default Environment"


class _FakeEnvFactory:
    @staticmethod
    def create_environment_manager(*_: Any, **__: Any) -> _FakeEnvManager:
        return _FakeEnvManager()


class _FakeAPIManager:
    """Fake APIManager returning one classification event that yields one alert."""

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def list_events(self, *_: Any, **__: Any):
        return {
            "data": {
                "activitySeriesConnection": {
                    "edges": [
                        {
                            "node": {
                                "id": "act-1",
                                "activitySeriesId": "series-1",
                                "objectId": "11111111-1111-1111-1111-111111111111",
                                "objectName": "TestObject",
                                "lastUpdated": "2026-07-19T10:00:00.000Z",
                                "activityConnection": {
                                    "nodes": [{"id": "n1", "message": RESULTS_MESSAGE}]
                                },
                            }
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

    def get_closest_snapshot(self, *_: Any, **__: Any):
        return {
            "data": {
                "allSnapshotsClosestToPointInTime": [
                    {
                        "snapshot": {
                            "id": "33333333-3333-3333-3333-333333333333",
                            "date": "2026-07-18T10:00:00.000Z",
                        }
                    }
                ]
            }
        }

    def get_classification_object_detail(self, *_: Any, **__: Any):
        return {
            "data": {
                "policyObj": {
                    "riskLevel": "HIGH_RISK",
                    "rootFileResult": {"hits": {"violations": 7, "totalHits": 20}},
                    "policySummaries": [{"name": "PII"}],
                }
            }
        }


@pytest.fixture
def connector(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = _load_connector_module()

    fake_siemplify = _FakeSiemplify()
    monkeypatch.setattr(module, "SiemplifyConnectorExecution", lambda *_, **__: fake_siemplify)
    monkeypatch.setattr(module, "APIManager", _FakeAPIManager)
    monkeypatch.setattr(module, "GetEnvironmentCommonFactory", _FakeEnvFactory)
    monkeypatch.setattr(module, "is_overflowed", lambda *_, **__: False)
    monkeypatch.setattr(module, "is_approaching_timeout", lambda *_, **__: False)

    params = {
        "Service Account JSON": (
            '{"client_id": "cid", "client_secret": "sec", '
            '"access_token_uri": "https://test.rubrik.com/api/client_token"}'
        ),
        "Verify SSL": False,
        "Search Time Period (Days)": 1,
        "PythonProcessTimeout": 300,
        "EventClassId": "eventName",
        "DeviceProductField": "Rubrik Security Cloud",
    }

    def _extract(_siemplify, param_name, default_value=None, **__):
        return params.get(param_name, default_value)

    monkeypatch.setattr(module, "extract_connector_param", _extract)

    module._test_siemplify = fake_siemplify  # type: ignore[attr-defined]
    module._test_params = params  # type: ignore[attr-defined]
    return module


class TestClassificationEventsConnector:
    def test_creates_alert_for_object_with_violations(self, connector: ModuleType) -> None:
        # Test run avoids the checkpoint file read/write on disk.
        connector.main(is_test_run=True)

        package = connector._test_siemplify.returned_package
        assert package is not None
        assert len(package) == 1

    def test_no_alert_when_no_violations(
        self, connector: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _NoViolationManager(_FakeAPIManager):
            def get_classification_object_detail(self, *_: Any, **__: Any):
                return {"data": {"policyObj": {"rootFileResult": {"hits": {"violations": 0}}}}}

        monkeypatch.setattr(connector, "APIManager", _NoViolationManager)

        connector.main(is_test_run=True)

        package = connector._test_siemplify.returned_package
        assert package is not None
        assert len(package) == 0

    def test_no_alert_when_no_events(
        self, connector: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _NoEventsManager(_FakeAPIManager):
            def list_events(self, *_: Any, **__: Any):
                return {
                    "data": {
                        "activitySeriesConnection": {
                            "edges": [],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }

        monkeypatch.setattr(connector, "APIManager", _NoEventsManager)

        connector.main(is_test_run=True)

        package = connector._test_siemplify.returned_package
        assert package is not None
        assert len(package) == 0
