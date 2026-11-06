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

"""Tests configuration file"""
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
from google_cloud_asset_inventory.core.GoogleCloudAssetInventoryManager import (
    GoogleCloudAssetInventoryManager,
)
from google_cloud_asset_inventory.core.exceptions import (
    GoogleCloudAssetInventoryError,
    ProjectOrOrganizationNotFoundError,
)
from google_cloud_asset_inventory.tests import const


@pytest.fixture
def assetinventory_manager(mocker) -> GoogleCloudAssetInventoryManager:
    """Asset Inventory Manager

    Args:
        mocker: MockerFixture

    Returns:
        GoogleCloudAssetInventoryManager
        """
    with open(const.CONFIG_FILE_NAME, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    api_root = config.get("API Root")
    organization_id = config.get("Organization ID")
    project_id = config.get("Project ID")
    user_service_account = config.get("User Service Account", "{}")
    workload_identity_email = config.get("Workload Identity Email")
    quota_project_id = config.get("Quota Project ID")
    verify_ssl = bool(config.get("Verify SSL"))
    mocker.patch(
        "google_cloud_asset_inventory.core."
        "GoogleCloudAssetInventoryManager.build_credentials_from_sa",
        return_value=mocker.Mock()
    )
    mocker.patch(
        "google_cloud_asset_inventory.core."
        "GoogleCloudAssetInventoryManager.get_http_client",
        return_value=mocker.Mock()
    )

    manager = GoogleCloudAssetInventoryManager(
        api_root=api_root,
        organization_id=organization_id,
        project_id=project_id,
        workload_identity_email=workload_identity_email,
        quota_project_id=quota_project_id,
        logger=None,
        service_account_=user_service_account,
        verify_ssl=verify_ssl
    )

    return manager

@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test connectivity function to raise
    Google Cloud Asset Inventory exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudAssetInventoryError("Connectivity error")
    monkeypatch.setattr(
        GoogleCloudAssetInventoryManager,
        "test_connectivity",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_resource_details_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test get_resource_details function to raise
    Google Cloud Asset Inventory exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudAssetInventoryError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudAssetInventoryManager,
        "get_resource_details",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_resource_snapshots_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test get_resource_snapshots function to raise
    Google Cloud Asset Inventory exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudAssetInventoryError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudAssetInventoryManager,
        "get_resource_snapshots",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_list_service_account_roles_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test list_service_account_roles function to raise
    Google Cloud Asset Inventory exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise GoogleCloudAssetInventoryError("Hash data error")
    monkeypatch.setattr(
        GoogleCloudAssetInventoryManager,
        "analyze_iam_policy",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_project_not_found_failure_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test mock_project_not_found_failure function to raise
    Google Cloud Asset Inventory exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise ProjectOrOrganizationNotFoundError("An error occured")
    monkeypatch.setattr(
        GoogleCloudAssetInventoryManager,
        "get_resource_details",
        mock_raise_manager_error,
    )
