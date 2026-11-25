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

import json
from collections import namedtuple
from typing import TYPE_CHECKING

import pytest

from google_cloud_recommender.core import authentication
from google_cloud_recommender.core.exceptions import GoogleCloudRecommenderError
from google_cloud_recommender.core.GoogleCloudRecommenderManager import (
    GoogleCloudRecommenderManager,
)
from google_cloud_recommender.tests.common import CONFIG_PATH, TESTS_DIR

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from TIPCommon.types import JSON

GoogleAPIResponse = namedtuple(
    'GoogleAPIResponse',
    ['response_info', 'content'],
)

# Constants
RECOMMENDATION_NAME = (
    "projects/xxxxxxx/locations/global/recommenders/"
    "google.iam.policy.Recommender/recommendations/xxxxxxxx"
)
RECOMMENDER_SUBTYPE = "REMOVE_ROLE"
DUMMY_CONTENT = {"status": "200"}
DEFAULT_VALUE = "Default Value"
RECOMMENDATION_DESCRIPTION = "description"
RECOMMENDATION_DESCRIPTION_EXPECTED = (
    "This role has not been used during the observation window."
)
ZERO_LENGTH = 0
DEFAULT_LENGTH = 1
EMPTY_JSON = {}
INVALID_VALUE = "invalid"



class CustomReponse:
    """A class to represent a custom JSON response.

    Attributes:
        _result (JSON): The internal storage for a JSON data

    Methods:
        data: Property that gets or sets the JSON data
    """

    def __init__(self, initial_data: JSON | None = None) -> None:
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
    def data(self, json_data: JSON) -> None:
        """Sets the JSON data

        Args:
            JSON: The store JSON data.
        """
        self._result = json_data


@pytest.fixture
def recommender_manager(mocker: MockerFixture) -> GoogleCloudRecommenderManager:
    """Create a GoogleCloudRecommenderManager instance with mocked authentication."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    api_root = config.get("API Root")
    organization_id = config.get("Organization ID")
    project_id = config.get("Project ID")
    quota_project_id = config.get("Quota Project ID")
    workload_identity_email = config.get("Workload Identity Email")
    user_service_account = config.get("User Service Account")
    verify_ssl = bool(config.get("Verify SSL"))

    mocker.patch.object(authentication, "create_session", return_value=mocker.Mock())
    mocker.patch.object(
        authentication,
        "get_authentication_credentials_or_raise_error",
        return_value=mocker.Mock(),
    )

    return GoogleCloudRecommenderManager(
        api_root=api_root,
        organization_id=organization_id,
        project_id=project_id,
        quota_project_id=quota_project_id,
        workload_identity_email=workload_identity_email,
        siemplify_logger=mocker.MagicMock(),
        user_service_account=user_service_account,
        verify_ssl=verify_ssl,
    )

class TestGoogleCloudRecommender:
    """
    GoogleCloudRecommender test cases
    """

    def test_connectivity_success(
        self,
        mocker: MockerFixture,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """Test connectivity success.

        Args:
            mocker: MockerFixture
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'list_recommendations.json'
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        recommender_manager.session.request = mocker.Mock(
            return_value=GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=json.dumps(custom_response.data[0]),
            )
        )

        assert recommender_manager.test_connectivity() == None

    def test_get_recommendation(
        self,
        mocker: MockerFixture,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test the get recommendation success

        Args:
            mocker: MockerFixture
            recommender_manager: GoogleCloudRecommenderManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'get_recommendation.json'
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        recommender_manager.session.request = mocker.Mock(
            return_value=GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=json.dumps(custom_response.data[0]),
            )
        )
        result = recommender_manager.get_recommendation(
            recommendation_name=RECOMMENDATION_NAME
        )
        assert result != None
        assert result.name == RECOMMENDATION_NAME

    def test_update_recommendation(
        self,
        mocker: MockerFixture,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test the update recommendation success

        Args:
            mocker: MockerFixture
            recommender_manager: GoogleCloudRecommenderManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'update_recommendation.json'
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        recommender_manager.session.request = mocker.Mock(
            return_value=GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=json.dumps(custom_response.data[0]),
            )
        )
        result = recommender_manager.update_recommendation(
            recommendation_name=DEFAULT_VALUE,
            recommendation_type=DEFAULT_VALUE,
            etag=DEFAULT_VALUE,
        )
        assert result != None
        assert result.recommender_subtype == RECOMMENDER_SUBTYPE

    def test_list_recommendations(
        self,
        mocker: MockerFixture,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test the list recommendation success

        Args:
            mocker: MockerFixture
            recommender_manager: GoogleCloudRecommenderManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'list_recommendations.json'
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        recommender_manager.session.request = mocker.Mock(
            return_value=GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=json.dumps(custom_response.data[0]),
            )
        )
        result = recommender_manager.list_recommendations(
            resource_name=DEFAULT_VALUE,
            recommendation_location=DEFAULT_VALUE,
            recommendation_state=DEFAULT_VALUE,
            recommendation_priority=DEFAULT_VALUE,
            recommender_subtype=DEFAULT_VALUE,
            limit=DEFAULT_LENGTH
        )
        assert result != None
        assert result.raw_data == custom_response.data[0]

    def test_parse_recommendations(
        self,
        mocker: MockerFixture,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test the update recommendation status success

        Args:
            mocker: MockerFixture
            recommender_manager: GoogleCloudRecommenderManager

        Raises:
            AssertionError: If the result does not match
            the expected data.

        Returns:
            None
        """
        response_json = self.mock_get_response(
            'list_recommendations.json'
        )
        custom_response = CustomReponse()
        custom_response.data = response_json
        recommender_manager.session.request = mocker.Mock(
            return_value=GoogleAPIResponse(
                response_info=DUMMY_CONTENT,
                content=custom_response.data[0],
            )
        )
        result = recommender_manager.parse_recommendations(
            recommendation_to_be_applied=custom_response.data,
        )
        assert result != None
        assert result[0].description == RECOMMENDATION_DESCRIPTION_EXPECTED

    @pytest.mark.usefixtures("mock_test_connectivity_to_raise_manager_error")
    def test_connectivity_failure(
        self,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test connectivity failure

        Args:
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None

        Raises:
        - GoogleCloudRecommenderError
        """

        with pytest.raises(GoogleCloudRecommenderError):
            recommender_manager.test_connectivity()

    @pytest.mark.usefixtures("mock_get_recommendation_to_raise_manager_error")
    def test_get_recommendation_failure(
        self,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test get recommendation failure

        Args:
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None

        Raises:
        - GoogleCloudRecommenderError
        """

        with pytest.raises(GoogleCloudRecommenderError):
            recommender_manager.get_recommendation(
                recommendation_name=DEFAULT_VALUE
            )

    @pytest.mark.usefixtures(
        "mock_update_recommendation_to_raise_manager_error"
    )
    def test_update_recommendation_failure(
        self,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test update recommendation failure

        Args:
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None

        Raises:
        - GoogleCloudRecommenderError
        """

        with pytest.raises(GoogleCloudRecommenderError):
            recommender_manager.update_recommendation(
                recommendation_name=DEFAULT_VALUE,
                recommendation_type=DEFAULT_VALUE,
                etag=DEFAULT_VALUE,
            )

    @pytest.mark.usefixtures(
        "mock_list_recommendations_to_raise_manager_error"
    )
    def test_list_recommendations_failure(
        self,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test list recommendations failure

        Args:
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None

        Raises:
        - GoogleCloudRecommenderError
        """

        with pytest.raises(GoogleCloudRecommenderError):
            recommender_manager.list_recommendations(
                resource_name=DEFAULT_VALUE,
                recommendation_location=DEFAULT_VALUE,
                recommendation_state=DEFAULT_VALUE,
                recommendation_priority=DEFAULT_VALUE,
                recommender_subtype=DEFAULT_VALUE,
                limit=DEFAULT_LENGTH
            )

    @pytest.mark.usefixtures(
        "mock_parse_recommendations_to_raise_manager_error"
    )
    def test_parse_recommendations_failure(
        self,
        recommender_manager: GoogleCloudRecommenderManager
    ) -> None:
        """
        Test parse recommendations failure

        Args:
            recommender_manager: GoogleCloudRecommenderManager

        Returns:
            None

        Raises:
        - GoogleCloudRecommenderError
        """

        with pytest.raises(GoogleCloudRecommenderError):
            recommender_manager.parse_recommendations(
                recommendation_to_be_applied=DEFAULT_VALUE,
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

        with (TESTS_DIR / file_name).open(encoding="utf-8") as f:
            return json.load(f)
