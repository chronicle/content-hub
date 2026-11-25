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

from __future__ import annotations

from collections import namedtuple
import json
from typing import TYPE_CHECKING

import pytest
from TIPCommon.types import JSON

from google_cloud_policy_intelligence.core.exceptions import (
    GoogleCloudPolicyIntelligenceError,
)
from google_cloud_policy_intelligence.core.GoogleCloudPolicyIntelligenceManager import (
    GoogleCloudPolicyIntelligenceManager,
)
from google_cloud_policy_intelligence.tests.common import CONFIG_PATH, TESTS_DIR

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

GoogleAPIResponse = namedtuple(
    'GoogleAPIResponse',
    ['response_info', 'content'],
)

# Constants
RESOURCE_NAME = ["resource name"]
DUMMY_CONTENT = {"status": 200}


@pytest.fixture
def manager(mocker: MockerFixture) -> GoogleCloudPolicyIntelligenceManager:
    """Create a GoogleCloudPolicyIntelligenceManager with a mocked HTTP client."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    api_root = config.get("API Root")
    project_id = config.get("Project ID")
    user_service_account = config.get("User Service Account", "{}")
    quota_project_id = config.get("Quota Project ID", "")
    workload_identity_email = config.get(
        "Workload Identity Email",
        ""
    )
    location_id = config.get("Location ID", "")
    verify_ssl = bool(config.get("Verify SSL"))
    # mocker.patch('UtilsManager.parse_string_to_dict', return_value=mocker.Mock())
    mocker.patch.object(GoogleCloudPolicyIntelligenceManager, '_prepare_http_client', return_value=mocker.Mock())
    cloud_manager = GoogleCloudPolicyIntelligenceManager(
        api_root=api_root,
        project_id=project_id,
        logger=None,
        service_account_=user_service_account,
        quota_project_id=quota_project_id,
        workload_identity_email=workload_identity_email,
        location_id=location_id,
        verify_ssl=verify_ssl
    )

    return cloud_manager


class CustomResponse:
    """A class to represent a custom JSON response.

    Attributes:
        _result (JSON): The internal storage for a JSON data

    Methods:
        data: Property that gets or sets the JSON data
    """

    def __init__(self,initial_data: JSON = None) -> None:
        """Constructs a new CustomResponse object.

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
            json_data: The store JSON data.
        """
        self._result = json_data


class TestGoogleCloudPolicyIntelligence:
    """
    GoogleCloudPolicyIntelligence test cases
    """

    def test_connectivity_success(self, mocker, manager) -> None:
        """Test connectivity success.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'search_service_account_activity.json'
        )
        custom_response = CustomResponse()
        custom_response.data = response_json
        manager.http_client = mocker.Mock()
        manager.http_client.request.return_value = GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=custom_response.data,
            )

        assert manager.test_connectivity() is None

    def test_search_service_account_activity(
        self,
        mocker,
        manager
    ) -> None:
        """
        Test the search service account activity success

        Raises:
            AssertionError: If the result of the search does not match
            the expected project name and remove role.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'search_service_account_activity.json'
        )
        custom_response = CustomResponse()
        custom_response.data = response_json
        manager.http_client = mocker.Mock()
        manager.http_client.request.return_value = GoogleAPIResponse(
            response_info=DUMMY_CONTENT,
            content=json.dumps(custom_response.data),
        )

        result = manager.search_service_account_activity(RESOURCE_NAME)

        assert result != []

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_failure(self, manager) -> None:
        """
        Test connectivity failure

        Returns:
            None

        Raises:
        - GoogleCloudPolicyIntelligenceError
        """

        with pytest.raises(GoogleCloudPolicyIntelligenceError):
            manager.test_connectivity()

    @pytest.mark.usefixtures("mock_account_activity_to_raise_manager_error")
    def test_search_service_account_activity_failure(self, manager) -> None:
        """
        Test search service account activity failure

        Returns:
            None

        Raises:
        - GoogleCloudPolicyIntelligenceError
        """

        with pytest.raises(GoogleCloudPolicyIntelligenceError):
            manager.search_service_account_activity(RESOURCE_NAME)

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

        with (TESTS_DIR / file_name).open(encoding="utf-8") as response_file:
            return json.load(response_file)
