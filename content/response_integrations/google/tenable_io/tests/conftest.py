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

import dataclasses
import json
import pathlib
import sys
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest

from tenable_io.tests.core.session import TenableIOSession
from tenable_io.tests.core.product import TenableIOProduct
from tenable_io.tests.core.response import MockResponse



CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

MOCK_DATA_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: dict = json.loads(MOCK_DATA_PATH.read_text(encoding="utf-8"))


@dataclasses.dataclass(unsafe_hash=True)
class MockSiemplifyEntity:
    identifier: str
    entity_type: str
    additional_properties: dict[str, Any] = dataclasses.field(
        default_factory=dict,
        hash=False
    )
    is_enriched: bool = dataclasses.field(default=False, hash=False)
    is_suspicious: bool = dataclasses.field(default=False, hash=False)


@dataclasses.dataclass
class LegacyActionOutput:
    """
    Local replacement for MockActionOutput.
    Captures the output from siemplify.end().
    """
    output_message: str | None = None
    result_value: bool | str | None = None
    status: int | str | None = None
    is_success: bool = False

    def set_output(
        self,
        output_message: str,
        result_value: bool | str,
        status: int | str = 0
    ) -> None:
        """Mock implementation of siemplify.end()"""
        self.output_message = output_message
        self.result_value = result_value
        self.status = status
        self.is_success = result_value in [True, "true"]


@pytest.fixture(name="action_output")
def action_output_fixture() -> Generator[LegacyActionOutput, Any, None]:
    """Fixture providing an instance of LegacyActionOutput."""
    yield LegacyActionOutput()


@dataclasses.dataclass
class LegacyJsonResults:
    """
    Local replacement for MockJsonResults.
    Captures data from siemplify.result.add_result_json().
    """
    json_results: list | dict = dataclasses.field(
        default_factory=list
    )

    def set_json_results(self, json_data: list | dict) -> None:
        """Mock implementation of siemplify.result.add_result_json()"""
        if isinstance(self.json_results, list) and isinstance(json_data, dict):
            self.json_results.append(json_data)
        elif isinstance(self.json_results, dict) and isinstance(json_data, dict):
            self.json_results.update(json_data)
        else:
            self.json_results = json_data


@pytest.fixture(name="json_results")
def json_results_fixture() -> Generator[LegacyJsonResults, Any, None]:
    """Fixture providing an instance of LegacyJsonResults."""
    yield LegacyJsonResults()


@pytest.fixture(name="tenable_io_product")
def tenable_io_product_fixture() -> Generator[TenableIOProduct, Any, None]:
    """Provides an instance of the mock TenableIO product."""
    product = TenableIOProduct()
    for asset in MOCK_DATA.get("assets", []):
        product.add_asset(asset)
    for asset_id, vulns in MOCK_DATA.get("vulnerabilities", {}).items():
        product.add_vulnerabilities(asset_id, vulns)
    for policy in MOCK_DATA.get("policies", []):
        product.add_policy(policy)
    for scanner in MOCK_DATA.get("scanners", []):
        product.add_scanner(scanner)
    yield product


@pytest.fixture(name="action_params")
def action_params_fixture() -> dict[str, Any]:
    """Fixture to hold action parameters. Tests can modify this dictionary."""
    return {}


@pytest.fixture(autouse=True)
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
    action_params: dict[str, Any]
) -> Generator[MagicMock, Any, None]:
    """
    (autouse=True)
    Fully mocks the SiemplifyAction object for legacy scripts.
    """
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()
    mock_api.environment = "DefaultEnvironment"
    mock_api.integration_instance = "DefaultInstance"
    mock_api.LOGGER.error.side_effect = lambda msg, *args, **kwargs: print(
        f"DEBUG_LOGGER_ERROR: {msg}",
        file=sys.stdout
    )
    mock_api.LOGGER.info.side_effect = lambda msg, *args, **kwargs: print(
        f"DEBUG_LOGGER_INFO: {msg}",
        file=sys.stdout
    )
    mock_api.LOGGER.exception.side_effect = lambda e, *args, **kwargs: print(
        f"DEBUG_LOGGER_EXCEPTION: {e}",
        file=sys.stdout
    )

    mock_api.execution_deadline_unix_time_ms = 9999999999999

    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results
    mock_api.result.add_entity_table = MagicMock()

    enriched_entities = []

    def mock_update_entities(entities):
        for e in entities:
            if hasattr(e, "is_enriched") and e.is_enriched:
                enriched_entities.append(e)

    mock_api.update_entities.side_effect = mock_update_entities

    mock_api.target_entities = []
    mock_api.end.side_effect = action_output.set_output

    scripts_to_patch = [
        "tenable_io.actions.ListEndpointVulnerabilities",
        "tenable_io.actions.ScanEndpoints",
        "tenable_io.actions.EnrichEntities"
    ]

    for script in scripts_to_patch:
        monkeypatch.setattr(
            f"{script}.SiemplifyAction",
            lambda: mock_api,
        )

    def mock_extract_configuration_param(
        siemplify_obj: Any,
        provider_name: str,
        param_name: str,
        **kwargs: Any
    ) -> Any:
        _ = siemplify_obj
        _ = provider_name
        default_value = kwargs.get("default_value")
        val = CONFIG.get(param_name)
        if val is None and default_value is not None:
            return default_value
        return val

    for script in scripts_to_patch:
        monkeypatch.setattr(
            f"{script}.extract_configuration_param",
            mock_extract_configuration_param,
        )

    def mock_extract_action_param(
        siemplify_obj: Any,
        param_name: str,
        **kwargs: Any
    ) -> Any:
        _ = siemplify_obj
        default_value = kwargs.get("default_value")
        val = action_params.get(param_name)
        if val is None and default_value is not None:
            return default_value
        return val

    for script in scripts_to_patch:
        monkeypatch.setattr(
            f"{script}.extract_action_param",
            mock_extract_action_param,
        )

    yield mock_api


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    tenable_io_product: TenableIOProduct
) -> Generator[TenableIOSession, Any, None]:
    session = TenableIOSession(tenable_io_product, MOCK_DATA)
    """
    (autouse=True)
    Patches the requests.Session used by TenableIOManager.
    """

    monkeypatch.setattr("requests.Session.request", mock_request)
    yield session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
