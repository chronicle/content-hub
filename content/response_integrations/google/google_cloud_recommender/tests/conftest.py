
"""
Tests configuration file
"""
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
import pytest
from _pytest.monkeypatch import MonkeyPatch
from google_cloud_recommender.core.GoogleCloudRecommenderManager import (
    GoogleCloudRecommenderManager,
)
from google_cloud_recommender.core.exceptions import (
    GoogleCloudRecommenderError,
)


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test connectivity function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudRecommenderError("Connectivity error")
    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "test_connectivity",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_recommendation_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test get recommendation function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudRecommenderError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "get_recommendation",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_update_recommendation_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test update recommendation function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudRecommenderError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "update_recommendation",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_list_recommendations_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test list recommendations function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudRecommenderError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "list_recommendations",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_parse_recommendations_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test parse recommendations function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudRecommenderError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "parse_recommendations",
        mock_raise_manager_error,
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
