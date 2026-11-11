"""Tests configuration file"""
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
from intezer.core.IntezerManager import (
    IntezerManager,
)
from intezer.core.exceptions import (
    IntezerManagerError,
    IntezerBadRequestError,
)
from intezer.tests import const

@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test connectivity function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Connectivity error")
    monkeypatch.setattr(
        IntezerManager,
        "test_connectivity",
        mock_raise_manager_error,
    )

@pytest.fixture
def intezer_manager():
    """intezer manager function load config from config.json file.

    Returns:
        Manager
    """
    with open(const.CONFIG_FILE_NAME, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    api_root = config.get("API Root")
    api_key = config.get("API key")
    verify_ssl = bool(config.get("Verify SSL"))

    manager = IntezerManager(
        api_root=api_root,
        api_key=api_key,
        verify_ssl=verify_ssl
    )

    return manager

@pytest.fixture
def mock_get_detonate_file_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("IntezerNotFoundError")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_file",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_detonate_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate_hash function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Detonate Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_index_id_from_file_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_index_id_from_file_hash function
        to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Index Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_index_id_from_file_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_unset_index_file_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test unset_index_file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Unset Index File Error")
    monkeypatch.setattr(
        IntezerManager,
        "unset_index_file",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_suspicious_email_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_suspicious_email function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerBadRequestError("Bad Request Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_suspicious_email",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_detonate_url_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate_url function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Detonate URL Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_url",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_alert_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_alert function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Alert Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_alert",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_file_report_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_file_report function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get File Report Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_file_report",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_url_report_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_url_report function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get URl Report Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_url_report",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_alert_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_alert function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Submit Alert Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_alert",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_hash file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Submit Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_is_analysis_completed_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test is_analysis_completed function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "is_analysis_completed",
        mock_raise_manager_error,
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
