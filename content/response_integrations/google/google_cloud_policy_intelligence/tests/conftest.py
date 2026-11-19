
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
from google_cloud_policy_intelligence.core.GoogleCloudPolicyIntelligenceManager import (
    GoogleCloudPolicyIntelligenceManager,
)
from google_cloud_policy_intelligence.core.exceptions import (
    GoogleCloudPolicyIntelligenceError,
)


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test connectivity function to raise
    google cloud policy intelligence exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudPolicyIntelligenceError("Connectivity error")
    monkeypatch.setattr(
        GoogleCloudPolicyIntelligenceManager,
        "test_connectivity",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_account_activity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test search service account activity function to raise
    google cloud policy intelligence exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudPolicyIntelligenceError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudPolicyIntelligenceManager,
        "search_service_account_activity",
        mock_raise_manager_error,
    )
