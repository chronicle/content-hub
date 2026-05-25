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

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from TIPCommon.data_models import InstalledIntegrationInstance, UserDetails
from TIPCommon.rest.soar_api import (
    get_case_insights,
    get_installed_integrations_of_environment,
    get_siemplify_user_details,
    get_user_profile_cards,
    search_cases_by_everything,
)

if TYPE_CHECKING:
    from TIPCommon.rest.soar_platform_clients.legacy_soar_api import LegacySoarApi
    from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi


@pytest.fixture
def mock_get_soar_client_one_platform(
    mocker: MockerFixture, mock_oneplatform_client: "OnePlatformSoarApi"
) -> MagicMock:
    mock_get_client = mocker.patch("TIPCommon.rest.soar_api.get_soar_client")
    mock_get_client.return_value = mock_oneplatform_client
    return mock_get_client


@pytest.fixture
def mock_get_soar_client_legacy(mocker: MockerFixture, mock_legacy_client: "LegacySoarApi") -> MagicMock:
    mock_get_client = mocker.patch("TIPCommon.rest.soar_api.get_soar_client")
    mock_get_client.return_value = mock_legacy_client
    return mock_get_client


def test_get_user_profile_cards_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_user_profile_cards wrapper function formats output under One Platform API client."""
    mock_oneplatform_client.get_users_profile_cards = mocker.MagicMock(return_value=[{"username": "user1"}])

    res = get_user_profile_cards(mock_chronicle_soar)

    assert res == {"objectsList": [{"username": "user1"}]}
    params: Any = mock_oneplatform_client.params
    assert params.page_size == 20


def test_get_user_profile_cards_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_user_profile_cards wrapper function validates and returns JSON under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"objectsList": [{"username": "user1"}]}
    mock_legacy_client.get_users_profile_cards = mocker.MagicMock(return_value=mock_response)

    res = get_user_profile_cards(mock_chronicle_soar)

    assert res == {"objectsList": [{"username": "user1"}]}


def test_get_installed_integrations_of_environment_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_installed_integrations_of_environment formats instances under One Platform client."""
    mock_oneplatform_client.get_installed_integrations_of_environment = mocker.MagicMock(
        return_value=[
            {
                "identifier": "id1",
                "integrationIdentifier": "intel_1",
                "environment": "Prod",
                "displayName": "Instance 1",
            }
        ]
    )

    res = get_installed_integrations_of_environment(mock_chronicle_soar, "Prod", "intel_1")

    assert len(res) == 1
    assert isinstance(res[0], InstalledIntegrationInstance)
    assert res[0].identifier == "id1"
    assert res[0].integration_identifier == "intel_1"
    assert res[0].environment_identifier == "Prod"
    assert res[0].instance_name == "Instance 1"


def test_get_installed_integrations_of_environment_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_installed_integrations_of_environment validates and handles 204 JSON under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "integrationInstances": [
            {
                "identifier": "id1",
                "integrationIdentifier": "intel_1",
                "environment": "Prod",
                "displayName": "Instance 1",
            }
        ]
    }
    mock_legacy_client.get_installed_integrations_of_environment = mocker.MagicMock(return_value=mock_response)

    res = get_installed_integrations_of_environment(mock_chronicle_soar, "Prod", "intel_1")

    assert len(res) == 1
    assert isinstance(res[0], InstalledIntegrationInstance)
    assert res[0].identifier == "id1"


def test_get_case_insights_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_case_insights wrapper function formats list output under One Platform client."""
    mock_oneplatform_client.get_case_insights = mocker.MagicMock(return_value=[{"title": "Insight 1"}])

    res = get_case_insights(mock_chronicle_soar, 1)

    assert len(res) == 1
    assert res[0]["title"] == "Insight 1"


def test_get_case_insights_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_case_insights wrapper function validates and aggregates results under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"activities": [{"title": "Insight 1"}]}
    mock_legacy_client.get_case_insights = mocker.MagicMock(return_value=mock_response)

    res = get_case_insights(mock_chronicle_soar, 1)

    assert len(res) == 1
    assert res[0]["title"] == "Insight 1"


def test_get_siemplify_user_details_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_siemplify_user_details formats user profile cards output under One Platform client."""
    mock_oneplatform_client.get_siemplify_user_details = mocker.MagicMock(
        return_value=[{"id": 42, "user_name": "test_user"}]
    )

    res = get_siemplify_user_details(mock_chronicle_soar, "some_search", False, 1, 10, "False")

    assert len(res) == 1
    assert isinstance(res[0], UserDetails)
    assert res[0].id_ == 42


def test_get_siemplify_user_details_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_siemplify_user_details validates and extracts objectsList under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"objectsList": [{"id": 42, "user_name": "test_user"}]}
    mock_legacy_client.get_siemplify_user_details = mocker.MagicMock(return_value=mock_response)

    res = get_siemplify_user_details(mock_chronicle_soar, "some_search", False, 1, 10, "False")

    assert len(res) == 1
    assert isinstance(res[0], UserDetails)
    assert res[0].id_ == 42


def test_search_cases_by_everything_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test search_cases_by_everything formats aggregated search output under One Platform client."""
    mock_oneplatform_client.search_cases_by_everything = mocker.MagicMock(return_value=[{"id": 1}, {"id": 2}])

    res = search_cases_by_everything(mock_chronicle_soar, {"query": "something"})

    assert res == {"results": [{"id": 1}, {"id": 2}]}


def test_search_cases_by_everything_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test search_cases_by_everything validates and returns json output under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": 1}, {"id": 2}]}
    mock_legacy_client.search_cases_by_everything = mocker.MagicMock(return_value=mock_response)

    res = search_cases_by_everything(mock_chronicle_soar, {"query": "something"})

    assert res == {"results": [{"id": 1}, {"id": 2}]}
