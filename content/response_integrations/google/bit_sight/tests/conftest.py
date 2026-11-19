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
import json

import pytest
from _pytest.monkeypatch import MonkeyPatch

from bit_sight.core.BitSightExceptions import BitSightException
from bit_sight.core.BitSightManager import BitSightManager
from integration_testing.logger import Logger


class MockResponse:

    def __init__(self, json_data, status_code) -> None:
        self.json_data = json_data
        self.status_code = status_code

    def json(self) -> dict:
        return self.json_data


@pytest.fixture(scope="module")
def bitsight_manager() -> BitSightManager:
    with open("config.json", "r") as f:
        data = f.read()

    config = json.loads(data)
    api_root = config.get("API Root")
    api_key = config.get("API Key")
    verify_ssl = config.get("Verify SSL")

    yield BitSightManager(
        api_root=api_root,
        api_key=api_key,
        verify_ssl=verify_ssl,
        siemplify_logger=Logger()
    )


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise BitSightException("An error occurred: 401 Client Error")

    monkeypatch.setattr(
        BitSightManager,
        'test_connectivity',
        mock_raise_manager_error
    )

@pytest.fixture
def mock_get_company_details_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise BitSightException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        BitSightManager,
        'get_company_details',
        mock_raise_manager_error
    )

@pytest.fixture
def mock_get_company_vulnerabilities_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise BitSightException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        BitSightManager,
        'get_company_vulnerabilities',
        mock_raise_manager_error
    )


def mock_get_companies_response(*args, **kwargs) -> MockResponse:
    with open("companies.json", "r") as f:
        data = f.read()
    companies = json.loads(data)
    return MockResponse(companies, 200)


def mock_get_vulnerabilities_response(*args, **kwargs) -> MockResponse:
    with open("vulnerabilities.json", "r") as f:
        data = f.read()
    companies = json.loads(data)
    return MockResponse(companies, 200)


@pytest.fixture
def mock_get_companies_response_pytest(monkeypatch: MonkeyPatch, *args, **kwargs):
    def mock_company_response(*args, **kwargs):
        with open("companies.json", "r") as f:
            data = f.read()
        companies = json.loads(data)
        return MockResponse(companies, 200)
    monkeypatch.setattr(
        BitSightManager,
        'make_request',
        mock_company_response
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session

