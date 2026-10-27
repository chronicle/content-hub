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

import copy
import urllib.parse
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, call

import pytest
import requests

from TIPCommon.exceptions import (
    EmptyMandatoryValues,
    InternalJSONDecoderError,
    ParameterValidationError,
)
from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
    expected_filter = "environment eq '*'"
    expected_url = f"https://mock-soar-api.com/integrations/intel_1/integrationInstances?$filter={urllib.parse.quote(expected_filter)}&pageSize=1000"
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        expected_url,
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
    expected_filter = "environment eq 'Production Environment'"
    expected_url = f"https://mock-soar-api.com/integrations/intel_1/integrationInstances?$filter={urllib.parse.quote(expected_filter)}&pageSize=1000"
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        expected_url,
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
        json={"query": "something", "pageSize": 10, "requestedPage": 0},
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
            {"query": "something", "pageSize": 2, "requestedPage": 0},
            {"format": "camel"},
        ),
        (
            "POST",
            "https://mock-soar-api.com/legacySearches:legacyCaseSearchEverything",
            {"query": "something", "pageSize": 2, "requestedPage": 1},
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


def test_save_or_update_job_success(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test save_or_update_job makes the correct PATCH request to One Platform API on success."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    job_data = {
        "name": "projects/p/locations/l/instances/i/integrations/int/jobs/j/jobInstances/ji",
        "parameters": [{"displayName": "param1", "value": "val1"}],
    }
    params: Any = client.params
    params.job_data = job_data

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_chronicle_soar.session.request.return_value = mock_response

    res = client.save_or_update_job()

    assert res == mock_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "PATCH",
        "https://mock-soar-api.com/integrations/int/jobs/j/jobInstances/ji",
        params={"updateMask": "parameters"},
        json={"parameters": [{"displayName": "param1", "value": "val1"}]},
    )


def test_save_or_update_job_missing_name(mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock) -> None:
    """Test save_or_update_job raises EmptyMandatoryValues if 'name' is missing."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.job_data = {
        "parameters": [{"displayName": "param1", "value": "val1"}],
    }

    with pytest.raises(EmptyMandatoryValues) as exc_info:
        client.save_or_update_job()

    assert "Job data must include a 'name' field" in str(exc_info.value)


def test_save_or_update_job_missing_parameters(mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock) -> None:
    """Test save_or_update_job raises EmptyMandatoryValues if 'parameters' is missing."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.job_data = {
        "name": "projects/p/locations/l/instances/i/integrations/int/jobs/j/jobInstances/ji",
    }

    with pytest.raises(EmptyMandatoryValues) as exc_info:
        client.save_or_update_job()

    assert "Job data is missing 'parameters' field" in str(exc_info.value)


def test_save_or_update_job_invalid_resource_path(
    mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test save_or_update_job raises ParameterValidationError if 'name' does not contain 'integrations/'."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.job_data = {
        "name": "projects/p/locations/l/instances/i/jobs/j/jobInstances/ji",
        "parameters": [{"displayName": "param1", "value": "val1"}],
    }

    with pytest.raises(ParameterValidationError) as exc_info:
        client.save_or_update_job()

    assert "Cannot parse resource path" in str(exc_info.value)
    assert 'Invalid parameter "name"' in str(exc_info.value)


def test_get_traking_list_records_filtered_url_encoded(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:

    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.environment = "Indevis GmbH & Co. KG"
    params.category_name = "Indevis_Test_&_München"
    params.entity_id = "192.168.1.100"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"customLists": [{"id": "list_1"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    records = client.get_traking_list_records_filtered()

    assert records == [{"id": "list_1"}]
    expected_filter = client._build_tracking_list_filter_string(
        params.category_name, params.entity_id, environment=params.environment
    )
    expected_url = f"https://mock-soar-api.com/system/settings/customLists?$filter={urllib.parse.quote(expected_filter)}&pageSize=1000"
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        expected_url,
        params=None,
        json=None,
    )


def test_get_traking_list_record_url_encoded(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_traking_list_record URL-encodes special characters in OData filter."""

    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.category_name = "Indevis_Test_&_München"
    params.entity_id = "192.168.1.100"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"customLists": [{"id": "list_2"}], "nextPageToken": None}
    mock_chronicle_soar.session.request.return_value = mock_response

    records = client.get_traking_list_record()

    assert records == [{"id": "list_2"}]
    expected_filter = client._build_tracking_list_filter_string(params.category_name, params.entity_id)
    expected_url = f"https://mock-soar-api.com/system/settings/customLists?$filter={urllib.parse.quote(expected_filter)}&pageSize=1000"
    mock_chronicle_soar.session.request.assert_called_once_with(
        "GET",
        expected_url,
        params=None,
        json=None,
    )


def test_attach_case_playbook_to_case_without_original_identifier(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test attach_case_playbook_to_case sends correct payload when original_workflow_definition_identifier is not set."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 123
    params.playbook_name = "Case Triage"
    params.should_run_automatic = True
    params.original_workflow_definition_identifier = None

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_chronicle_soar.session.request.return_value = mock_response

    res = client.attach_case_playbook_to_case()

    assert res == mock_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/legacyPlaybooks:legacyAttachWorkflowToCase",
        params={"format": "camel"},
        json={
            "cyberCaseId": 123,
            "shouldRunAutomatic": True,
            "wfName": "Case Triage",
        },
    )


def test_attach_case_playbook_to_case_with_original_identifier(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test attach_case_playbook_to_case sends originalWorkflowDefinitionIdentifier when provided."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 456
    params.playbook_name = "Incident Playbook"
    params.should_run_automatic = False
    params.original_workflow_definition_identifier = "orig_wf_def_123"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_chronicle_soar.session.request.return_value = mock_response

    res = client.attach_case_playbook_to_case()

    assert res == mock_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/legacyPlaybooks:legacyAttachWorkflowToCase",
        params={"format": "camel"},
        json={
            "cyberCaseId": 456,
            "shouldRunAutomatic": False,
            "wfName": "Incident Playbook",
            "originalWorkflowDefinitionIdentifier": "orig_wf_def_123",
        },
    )


def test_get_enabled_workflow_cards(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test get_enabled_workflow_cards sends correct request payload and parameters."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.environment = "Production"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"payload": [{"id": "card_1"}]}
    mock_chronicle_soar.session.request.return_value = mock_response

    res = client.get_enabled_workflow_cards()

    assert res == mock_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/legacyPlaybooks:legacyGetEnabledWFCards",
        params={"format": "camel"},
        json={
            "caseEnvironment": "Production",
            "executionScope": "CASE",
        },
    )


def _build_http_response(
    status_code: int,
    body: bytes,
    url: str = "https://mock-soar-api.com/test",
) -> requests.Response:
    """Build a real requests.Response object for testing HTTP status and JSON validation."""
    response = requests.Response()
    response.status_code = status_code
    response._content = body
    response.encoding = "utf-8"
    response.url = url
    return response


@pytest.mark.parametrize(
    ("status_code", "error_body"),
    [
        (403, '{"error": {"code": 403, "message": "Permission chronicle.legacySoarUsers.get denied"}}'),
        (404, '{"error": {"code": 404, "message": "Requested entity was not found"}}'),
        (500, '{"error": {"code": 500, "message": "Internal server error"}}'),
    ],
)
def test_get_users_profile_cards_http_errors_raise_with_body(
    status_code: int,
    error_body: str,
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test get_users_profile_cards raises HTTPError with response body on 403, 404, and 500."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    mock_chronicle_soar.session.request.return_value = _build_http_response(
        status_code, error_body.encode("utf-8")
    )

    with pytest.raises(requests.HTTPError) as exc_info:
        client.get_users_profile_cards()

    assert str(status_code) in str(exc_info.value)
    assert error_body in str(exc_info.value)
    assert exc_info.value.response is not None
    assert exc_info.value.response.status_code == status_code


@pytest.mark.parametrize(
    ("status_code", "error_body"),
    [
        (403, '{"error": {"code": 403, "message": "Permission chronicle.legacySoarUsers.get denied"}}'),
        (404, '{"error": {"code": 404, "message": "Users endpoint not found"}}'),
        (500, '{"error": {"code": 500, "message": "Backend unavailable"}}'),
    ],
)
def test_get_siemplify_user_details_http_errors_raise_with_body(
    status_code: int,
    error_body: str,
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test get_siemplify_user_details raises HTTPError with response body on 403, 404, and 500."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    mock_chronicle_soar.session.request.return_value = _build_http_response(
        status_code, error_body.encode("utf-8")
    )

    with pytest.raises(requests.HTTPError) as exc_info:
        client.get_siemplify_user_details()

    assert str(status_code) in str(exc_info.value)
    assert error_body in str(exc_info.value)


@pytest.mark.parametrize(
    ("status_code", "raw_body"),
    [
        (200, b"{}"),
        (204, b""),
    ],
)
def test_paginate_results_empty_proto3_or_204_returns_empty_without_warning(
    status_code: int,
    raw_body: bytes,
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test legitimately empty 1P proto3 responses ({}) and 204 No Content return [] cleanly."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    mock_chronicle_soar.session.request.return_value = _build_http_response(status_code, raw_body)

    users = client.get_users_profile_cards()

    assert users == []
    mock_chronicle_soar.LOGGER.warn.assert_not_called()


def test_paginate_results_unexpected_root_key_logs_actual_top_level_keys(
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test 2xx response without expected root key logs actual top-level keys."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    mock_chronicle_soar.session.request.return_value = _build_http_response(
        200,
        b'{"users": [{"userName": "alice"}], "totalSize": 1}',
    )

    users = client.get_users_profile_cards()

    assert users == []
    mock_chronicle_soar.LOGGER.warn.assert_called_once()
    warn_msg = mock_chronicle_soar.LOGGER.warn.call_args[0][0]
    assert "legacySoarUsers" in warn_msg
    assert "['users', 'totalSize']" in warn_msg


def test_paginate_results_multi_page_http_error_propagates(
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test _paginate_results raises HTTPError when a later page fails instead of truncating."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    page_1 = _build_http_response(
        200,
        b'{"legacySoarUsers": [{"userName": "user1"}], "nextPageToken": "page_2_tok"}',
    )
    page_2 = _build_http_response(
        500,
        b'{"error": {"code": 500, "message": "Upstream timeout on page 2"}}',
    )
    mock_chronicle_soar.session.request.side_effect = [page_1, page_2]

    with pytest.raises(requests.HTTPError) as exc_info:
        client.get_users_profile_cards()

    assert "Upstream timeout on page 2" in str(exc_info.value)


def test_paginate_results_invalid_json_raises_decoder_error(
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test _paginate_results raises InternalJSONDecoderError on non-JSON 200 payload."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    mock_chronicle_soar.session.request.return_value = _build_http_response(
        200,
        b"<html>502 Bad Gateway</html>",
    )

    with pytest.raises(InternalJSONDecoderError):
        client.get_users_profile_cards()


@pytest.mark.parametrize("status_code", [403, 404, 500])
def test_audited_1p_methods_raise_http_error_with_body(
    status_code: int,
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test audited OnePlatformSoarApi methods raise HTTPError with response body on 403/404/500."""
    error_payload = f'{{"error": {{"code": {status_code}, "message": "API failure {status_code}"}}}}'.encode()

    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 101
    params.alert_identifier = "alert_1"
    params.message = "SLA pause"
    params.integration_name = "Tools"
    params.search_payload = {"query": "test"}

    for method_call in (
        client.get_case_overview_details,
        client.get_all_case_overview_details,
        client.pause_alert_sla,
        client.resume_alert_sla,
        client.get_investigator_data,
        client.get_ide_cards,
        client.get_simulated_cases,
        client.get_case_insights,
        client.search_cases_by_everything,
    ):
        mock_chronicle_soar.session.request.return_value = _build_http_response(status_code, error_payload)
        with pytest.raises(requests.HTTPError) as exc_info:
            method_call()
        assert f"API failure {status_code}" in str(exc_info.value)


def test_assign_case_to_user_ignores_alert_identifier_and_logs_info(
    mock_chronicle_soar: MagicMock,
    mock_get_sdk_api_uri: MagicMock,
) -> None:
    """Test 1P assign_case_to_user posts case-level bulk assign and logs alert_identifier note."""
    client = OnePlatformSoarApi(mock_chronicle_soar)
    params: Any = client.params
    params.case_id = 123
    params.assign_to = "secops_user_id"
    params.alert_identifier = "ALERT_123"

    ok_response = _build_http_response(200, b"{}")
    mock_chronicle_soar.session.request.return_value = ok_response

    res = client.assign_case_to_user()

    assert res == ok_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/cases:executeBulkAssign",
        params=None,
        json={"casesIds": [123], "userName": "secops_user_id"},
    )
    assert any(
        "alert_identifier" in call_args[0][0]
        for call_args in mock_chronicle_soar.LOGGER.info.call_args_list
    )
