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

"""Unit tests for GoogleCloudAssetInventory Integration."""
from collections import namedtuple
import json
import os
import pytest
from pytest_mock import MockerFixture

from TIPCommon.types import JSON

from google_cloud_asset_inventory.core.GoogleCloudAssetInventoryManager import (
    GoogleCloudAssetInventoryManager,
)
from google_cloud_asset_inventory.core.exceptions import (
    GoogleCloudAssetInventoryError,
    ProjectOrOrganizationNotFoundError,
)
from google_cloud_asset_inventory.tests import const
GoogleAPIResponse = namedtuple(
    "GoogleAPIResponse",
    ["response_info", "content"],
)


class CustomReponse:
    """A class to represent a custom JSON response.

    Attributes:
        _result (JSON): The internal storage for a JSON data

    Methods:
        data: Property that gets or sets the JSON data
    """

    def __init__(self,initial_data: JSON = None) -> None:
        """Consturcts a new CustomReponse object.

        Args:
            initial_data (JSON): An initial JSON data to store.
            Defaults to an empty dictionary.
        """
        self._result = initial_data or {}

    @property
    def data(self) -> JSON:
        """Returns the store JSON data.

        Returns:
            JSON: The store JSON data.
        """
        return self._result

    @data.setter
    def data(self, json_data: JSON):
        """Sets the JSON data

        Args:
            JSON: The store JSON data.
        """
        self._result = json_data

class TestGoogleCloudAssetInventory:
    """
    GoogleCloudAssetInventory test cases
    """

    def test_connectivity_success(
        self,
        mocker: MockerFixture,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """Test connectivity success.

        Args:
            mocker: MockerFixture
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_resource_details.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        assetinventory_manager.http_client = mocker.Mock()
        assetinventory_manager.http_client.request.return_value = GoogleAPIResponse(
            response_info=const.DUMMY_CONTENT,
            content=custom_response.data,
        )

        assert assetinventory_manager.test_connectivity() is None

    def test_get_resource_details_success(
        self,
        mocker: MockerFixture,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test the get_resource_details success

        Args:
            mocker: MockerFixture
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_resource_details.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        assetinventory_manager.http_client = mocker.Mock()
        assetinventory_manager.http_client.request.return_value = GoogleAPIResponse(
            response_info=const.DUMMY_CONTENT,
            content=json.dumps(custom_response.data),
        )
        result = assetinventory_manager.get_resource_details(
            const.DEFAULT_VALUE,
            const.DEFAULT_VALUE
        )
        response_resources_names = [
            resource.resource_name for resource in result
        ]
        assert response_resources_names[0] is not None
        assert response_resources_names[0] == const.RESOURCES_NAME

    def test_get_resource_snapshots_success(
        self,
        mocker: MockerFixture,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test the get_resource_snapshots success

        Args:
            mocker: MockerFixture
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "get_resource_snapshots.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        assetinventory_manager.http_client = mocker.Mock()
        assetinventory_manager.http_client.request.return_value = GoogleAPIResponse(
            response_info=const.DUMMY_CONTENT,
            content=json.dumps(custom_response.data),
        )
        result = assetinventory_manager.get_resource_snapshots(
            read_mask=const.DEFAULT_VALUE,
            asset_names=const.ASSET_NAME
        )
        response_asset_names = [
            snapshot.asset_name for snapshot in result
        ]
        assert response_asset_names[0] is not None
        assert response_asset_names[0] == const.ASSET_NAME_VALUE

    def test_list_service_account_roles_success(
        self,
        mocker: MockerFixture,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test the list_service_account_roles success

        Args:
            mocker: MockerFixture
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            "list_service_account_roles.json"
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        assetinventory_manager.http_client = mocker.Mock()
        assetinventory_manager.http_client.request.return_value = GoogleAPIResponse(
            response_info=const.DUMMY_CONTENT,
            content=json.dumps(custom_response.data),
        )
        result = assetinventory_manager.analyze_iam_policy(
            identity=const.DEFAULT_VALUE,
            roles=const.DEFAULT_VALUE,
            permissions=const.DEFAULT_VALUE,
            expand_roles=const.DEFAULT_VALUE
        )
        response_result = [aqr.raw_data for aqr in result]
        assert response_result[0] is not None
        assert (
            response_result[0].get(
                "attachedResourceFullName"
            ) == const.ATTACHED_RESOURCE_NAME
        )

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_failure(
        self,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test connectivity failure

        Args:
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None

        Raises:
        - assetinventory_manager
        """

        with pytest.raises(GoogleCloudAssetInventoryError):
            assetinventory_manager.test_connectivity()

    @pytest.mark.usefixtures("mock_get_resource_details_to_raise_manager_error")
    def test_get_resource_details_failure(
        self,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test get_resource_details failure

        Args:
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None

        Raises:
        - GoogleCloudAssetInventoryManager
        """

        with pytest.raises(GoogleCloudAssetInventoryError):
            assetinventory_manager.get_resource_details(
                const.DEFAULT_VALUE,
                const.DEFAULT_VALUE
            )

    @pytest.mark.usefixtures("mock_project_not_found_failure_to_raise_manager_error")
    def test_project_not_found_failure(
        self,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test project_not_found failure

        Args:
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None

        Raises:
        - GoogleCloudAssetInventoryManager
        """

        with pytest.raises(ProjectOrOrganizationNotFoundError):
            assetinventory_manager.get_resource_details(
                const.DEFAULT_VALUE,
                const.DEFAULT_VALUE
            )

    @pytest.mark.usefixtures("mock_get_resource_snapshots_to_raise_manager_error")
    def test_get_resource_snapshots_failure(
        self,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test get_resource_snapshots failure

        Args:
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None

        Raises:
        - GoogleCloudAssetInventoryManager
        """

        with pytest.raises(GoogleCloudAssetInventoryError):
            assetinventory_manager.get_resource_snapshots(
                read_mask=const.DEFAULT_VALUE,
                asset_names=const.ASSET_NAME
            )

    @pytest.mark.usefixtures("mock_list_service_account_roles_to_raise_manager_error")
    def test_list_service_account_roles_failure(
        self,
        assetinventory_manager: GoogleCloudAssetInventoryManager
    ) -> None:
        """
        Test list_service_account_roles failure

        Args:
            assetinventory_manager: GoogleCloudAssetInventoryManager

        Returns:
            None

        Raises:
        - GoogleCloudAssetInventoryManager
        """

        with pytest.raises(GoogleCloudAssetInventoryError):
            assetinventory_manager.analyze_iam_policy(
                identity=const.DEFAULT_VALUE,
                roles=const.DEFAULT_VALUE,
                permissions=const.DEFAULT_VALUE,
                expand_roles=const.DEFAULT_VALUE
            )

    def mock_get_response(self, file_name: str) -> JSON:
        """
        Load and return JSON content from a given file in the
        same directory as th script.

        Parameters:
        - file_name (str): The name of the file containing the JSON content.

        Returns:
        - JSON: The parse JSON content of the file.

        Raises:
        - FileNotFoundError: If the given file_name does not exist in the directory.
        - json.JSONDecoderError: If the file content is not valid JSON.
        """

        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, file_name), "r", encoding="utf-8") as f:
            response = json.load(f)
        return response
