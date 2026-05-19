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

import copy
from typing import Any
from unittest.mock import MagicMock, call

import requests
from pytest_mock import MockerFixture

from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi


def test_get_case_insights_single_page(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_case_insights returns insights from a single page response."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 123

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"activities": [{"insight_id": "i1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    insights = client.get_case_insights()

    assert insights == [{"insight_id": "i1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        "https://mock-soar-api.com/cases/123/activities?$filter=activityType eq 'CaseInsight'&pageSize=1000",
        params=None,
        json=None,
    )


def test_get_case_insights_multi_page(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_case_insights aggregates insights from multiple page responses."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 123

    mock_response_1 = mocker.MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {"activities": [{"insight_id": "i1"}], "nextPageToken": "token_abc"}

    mock_response_2 = mocker.MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {"activities": [{"insight_id": "i2"}], "nextPageToken": None}

    mock_chronicle_soar.session.request.side_effect = [mock_response_1, mock_response_2]

    insights = client.get_case_insights()

    assert insights == [{"insight_id": "i1"}, {"insight_id": "i2"}]
    assert mock_chronicle_soar.session.request.call_count == 2
    mock_chronicle_soar.session.request.assert_has_calls([
        call(
            "GET",
            "https://mock-soar-api.com/cases/123/activities?$filter=activityType eq 'CaseInsight'&pageSize=1000",
            params=None,
            json=None,
        ),
        call(
            "GET",
            "https://mock-soar-api.com/cases/123/activities?$filter=activityType eq 'CaseInsight'&pageSize=1000&pageToken=token_abc",
            params=None,
            json=None,
        ),
    ])


def test_get_installed_integrations_of_environment_shared_instances(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment with Shared Instances environment query."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.integration_identifier = "intel_1"
    params.environment = "Shared Instances"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"integrationInstances": [{"id": "inst_1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    instances = client.get_installed_integrations_of_environment()

    assert instances == [{"id": "inst_1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        "https://mock-soar-api.com/integrations/intel_1/integrationInstances?$filter=environment eq '*'&pageSize=1000",
        params=None,
        json=None,
    )


def test_get_installed_integrations_of_environment_specific_env(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment with a specific environment query."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.integration_identifier = "intel_1"
    params.environment = "Production Environment"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"integrationInstances": [{"id": "inst_1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    instances = client.get_installed_integrations_of_environment()

    assert instances == [{"id": "inst_1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        "https://mock-soar-api.com/integrations/intel_1/integrationInstances?$filter=environment eq 'Production Environment'&pageSize=1000",
        params=None,
        json=None,
    )


def test_get_users_profile_cards_default(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_users_profile_cards with default page size settings."""
    client = OnePlatformSoarApi(mock_chronicle_soar)

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"legacySoarUsers": [{"username": "user1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    users = client.get_users_profile_cards()

    assert users == [{"username": "user1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET", "https://mock-soar-api.com/legacySoarUsers?pageSize=1000", params=None, json=None
    )


def test_get_users_profile_cards_custom_page_size(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_users_profile_cards with a custom page size setting."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.page_size = 50

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"legacySoarUsers": [{"username": "user1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    users = client.get_users_profile_cards()

    assert users == [{"username": "user1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET", "https://mock-soar-api.com/legacySoarUsers?pageSize=50", params=None, json=None
    )


def test_get_siemplify_user_details(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_siemplify_user_details returns user profile cards under One Platform client."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.page_size = 20

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"legacySoarUsers": [{"username": "user1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    users = client.get_siemplify_user_details()

    assert users == [{"username": "user1"}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET", "https://mock-soar-api.com/legacySoarUsers?pageSize=20", params=None, json=None
    )


def test_search_cases_by_everything_single_page(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test search_cases_by_everything executes search successfully on a single page of results."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.search_payload = {"query": "something", "pageSize": 10}

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": 1}, {"id": 2}], "totalCount": 2}
    mock_chronicle_soar.session.request.return_value = mock_response

    cases = client.search_cases_by_everything()

    assert cases == [{"id": 1}, {"id": 2}]
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/legacySearches:legacyCaseSearchEverything",
        params={"format": "camel"},
        json={"query": "something", "pageSize": 10, "pageNumber": 0},
    )


def test_search_cases_by_everything_multi_page(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test search_cases_by_everything aggregates results across multiple search page POST requests."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.search_payload = {"query": "something", "pageSize": 2}

    mock_response_1 = mocker.MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {"results": [{"id": 1}, {"id": 2}], "totalCount": 3}

    mock_response_2 = mocker.MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {"results": [{"id": 3}], "totalCount": 3}

    recorded_calls: list[tuple] = []

    def mock_request(method: str, url: str, **kwargs: Any) -> MagicMock:
        recorded_calls.append((method, url, copy.deepcopy(kwargs.get("json")), kwargs.get("params")))
        if len(recorded_calls) == 1:
            return mock_response_1
        return mock_response_2

    mock_chronicle_soar.session.request.side_effect = mock_request

    cases = client.search_cases_by_everything()

    assert cases == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert len(recorded_calls) == 2
    assert recorded_calls == [
        (
            "POST",
            "https://mock-soar-api.com/legacySearches:legacyCaseSearchEverything",
            {"query": "something", "pageSize": 2, "pageNumber": 0},
            {"format": "camel"},
        ),
        (
            "POST",
            "https://mock-soar-api.com/legacySearches:legacyCaseSearchEverything",
            {"query": "something", "pageSize": 2, "pageNumber": 1},
            {"format": "camel"},
        ),
    ]


def test_search_cases_by_everything_error_stops_pagination(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test search_cases_by_everything stops pagination and returns accumulated results on error."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.search_payload = {"query": "something", "pageSize": 2}

    mock_response_1 = mocker.MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {"results": [{"id": 1}, {"id": 2}], "totalCount": 4}

    mock_response_2 = mocker.MagicMock()
    mock_response_2.status_code = 500

    # raise_for_status will raise requests.HTTPError
    mock_response_2.raise_for_status.side_effect = requests.HTTPError("Internal Server Error")

    mock_chronicle_soar.session.request.side_effect = [mock_response_1, mock_response_2]

    cases = client.search_cases_by_everything()

    assert cases == [{"id": 1}, {"id": 2}]
    assert mock_chronicle_soar.session.request.call_count == 2
