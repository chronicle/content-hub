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
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager
from forti_analyzer.core.FortiAnalyzerExceptions import FortiAnalyzerException

import pytest

from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 401 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'test_connectivity',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_device_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'get_device',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_find_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'find_alert',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_mark_as_read_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'mark_as_read',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_assign_user_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'assign_user',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_acknowledge_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'acknowledge_alert',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_add_comment_to_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'add_comment_to_alert',
        mock_raise_manager_error
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
