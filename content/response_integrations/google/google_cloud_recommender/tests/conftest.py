# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests configuration file."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from typing import TYPE_CHECKING

import pytest
import soar_sdk

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from google_cloud_recommender.core.exceptions import (
    GoogleCloudRecommenderError,  # noqa: E402
)
from google_cloud_recommender.core.GoogleCloudRecommenderManager import (  # noqa: E402
    GoogleCloudRecommenderManager,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test connectivity function to raise
    Google Cloud Recommender exception
    """
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
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
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
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
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
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
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
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
    def mock_raise_manager_error(*args: object, **kwargs: object) -> None:
        raise GoogleCloudRecommenderError("Hash data error")

    monkeypatch.setattr(
        GoogleCloudRecommenderManager,
        "parse_recommendations",
        mock_raise_manager_error,
    )
