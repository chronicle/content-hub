"""
Tests configuration file
"""
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
import pytest
from _pytest.monkeypatch import MonkeyPatch

from microsoft_intune.core.exceptions import (
    MicrosoftIntuneManagerError
)
from microsoft_intune.core.MicrosoftIntuneManager import (
    MicrosoftIntuneManager
)

@pytest.fixture
def mock_list_devices_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the list managed devices function to raise
    MS Intune  exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("List managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "list_managed_devices",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_locate_devices_to_raise_manager_error(
    monkeypatch: MonkeyPatch) -> None:
    """
    Mock the locate managed devices function to raise
    MS Intune exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("Locate managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "locate_managed_device",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_reset_devices_passcode_to_raise_manager_error(
    monkeypatch: MonkeyPatch) -> None:
    """
    Mock the reset managed devices passcode function to
    raise MS Intune exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("Reset managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "reset_managed_device_passcode",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_remote_devices_to_raise_manager_error(
    monkeypatch: MonkeyPatch) -> None:
    """
    Mock the remote managed devices function to
    raise MS Intune exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("Remote managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "remote_lock_managed_device",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_sync_devices_to_raise_manager_error(
    monkeypatch: MonkeyPatch) -> None:
    """
    Mock the sync managed devices function to
    raise MS Intune exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("Sync managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "sync_managed_device",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_wipe_devices_to_raise_manager_error(
    monkeypatch: MonkeyPatch) -> None:
    """
    Mock the wipe managed devices function to
    raise MS Intune exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise MicrosoftIntuneManagerError("Wipe managed devices error")

    monkeypatch.setattr(
        MicrosoftIntuneManager,
        "wipe_managed_device",
        mock_raise_manager_error,
    )
