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

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED

from salesforce.actions import ListCases
from salesforce.core.constants import DEFAULT_MAX_RECORDS, INVALID_MAX_RECORDS_MSG, MAX_RECORDS_LIMIT
from salesforce.core.SalesforceManager import CASE_PROPERTIES

if TYPE_CHECKING:
    from collections.abc import Iterator

CONFIG: dict[str, str] = {
    "Api Root": "https://example.my.salesforce.com",
    "Username": "user",
    "Password": "pass",
    "Token": "token",
    "Verify SSL": "false",
}


@pytest.fixture
def sf_cls() -> Iterator[MagicMock]:
    """Mock the Salesforce client class used by SalesforceManager."""
    with patch("salesforce.core.SalesforceManager.Salesforce") as salesforce_cls:
        salesforce_cls.return_value.query.return_value = {"records": [], "done": True}
        yield salesforce_cls


def run_list_cases(parameters: dict[str, Any]) -> MagicMock:
    """Execute ListCases.main() with a mocked SiemplifyAction."""
    with patch.object(ListCases, "SiemplifyAction") as action_cls:
        siemplify: MagicMock = action_cls.return_value
        siemplify.get_configuration.return_value = CONFIG
        siemplify.parameters = parameters
        ListCases.main()
    return siemplify


def test_list_cases_uses_default_limit_when_param_omitted(sf_cls: MagicMock) -> None:
    """Omitting Max Records To Return queries up to DEFAULT_MAX_RECORDS and attaches CSV + JSON."""
    records: list[dict[str, str]] = [
        {"Id": "500A", "CaseNumber": "00001001", "Subject": "First"},
        {"Id": "500B", "CaseNumber": "00001002", "Subject": "Second"},
    ]
    sf_cls.return_value.query.return_value = {"records": records, "done": True}

    siemplify = run_list_cases({})

    expected_query = (
        f"SELECT {', '.join(CASE_PROPERTIES)} FROM Case ORDER BY CreatedDate DESC LIMIT {DEFAULT_MAX_RECORDS}"
    )
    sf_cls.return_value.query.assert_called_once_with(expected_query)
    siemplify.result.add_data_table.assert_called_once()
    siemplify.result.add_result_json.assert_called_once_with(records)
    siemplify.end.assert_called_once_with("Found 2 cases.", "true")


def test_list_cases_respects_custom_max_records(sf_cls: MagicMock) -> None:
    """Providing Max Records To Return bounds both SOQL LIMIT and paginated results."""
    sf_cls.return_value.query.return_value = {
        "records": [{"Id": "500A", "CaseNumber": "00001001"}, {"Id": "500B", "CaseNumber": "00001002"}],
        "done": False,
        "nextRecordsUrl": "/services/data/v64.0/query/next",
    }
    sf_cls.return_value.query_more.return_value = {
        "records": [{"Id": "500C", "CaseNumber": "00001003"}, {"Id": "500D", "CaseNumber": "00001004"}],
        "done": False,
        "nextRecordsUrl": "/services/data/v64.0/query/next-2",
    }

    siemplify = run_list_cases({"Max Records To Return": "3"})

    expected_query = f"SELECT {', '.join(CASE_PROPERTIES)} FROM Case ORDER BY CreatedDate DESC LIMIT 3"
    sf_cls.return_value.query.assert_called_once_with(expected_query)
    sf_cls.return_value.query_more.assert_called_once_with("/services/data/v64.0/query/next", True)
    siemplify.result.add_result_json.assert_called_once_with([
        {"Id": "500A", "CaseNumber": "00001001"},
        {"Id": "500B", "CaseNumber": "00001002"},
        {"Id": "500C", "CaseNumber": "00001003"},
    ])
    siemplify.end.assert_called_once_with("Found 3 cases.", "true")


def test_list_cases_empty_results_succeeds_without_data_table(sf_cls: MagicMock) -> None:
    """Zero matching cases completes successfully with empty JSON list and no empty CSV table."""
    siemplify = run_list_cases({"Max Records To Return": "10"})

    siemplify.result.add_data_table.assert_not_called()
    siemplify.result.add_result_json.assert_called_once_with([])
    siemplify.end.assert_called_once_with("Found 0 cases.", "true")


@pytest.mark.parametrize(
    "raw_value",
    [
        pytest.param("0", id="zero"),
        pytest.param("-5", id="negative"),
        pytest.param(str(MAX_RECORDS_LIMIT + 1), id="above-max"),
        pytest.param("abc", id="non-integer"),
    ],
)
def test_list_cases_invalid_max_records_fails_before_connecting(sf_cls: MagicMock, raw_value: str) -> None:
    """Invalid Max Records To Return ends with EXECUTION_STATE_FAILED before authenticating."""
    siemplify = run_list_cases({"Max Records To Return": raw_value})

    siemplify.LOGGER.exception.assert_called_once()
    siemplify.end.assert_called_once_with(
        f'Error executing action "List Cases". Reason: {INVALID_MAX_RECORDS_MSG}',
        "false",
        EXECUTION_STATE_FAILED,
    )
    siemplify.result.add_result_json.assert_not_called()
    siemplify.result.add_data_table.assert_not_called()
    sf_cls.assert_not_called()


def test_list_cases_handles_query_timeout_or_api_error_cleanly(sf_cls: MagicMock) -> None:
    """Query timeouts or API errors log the exception and fail cleanly instead of crashing."""
    sf_cls.return_value.query.side_effect = TimeoutError("Read timed out")

    siemplify = run_list_cases({})

    siemplify.LOGGER.exception.assert_called_once()
    siemplify.end.assert_called_once_with(
        'Error executing action "List Cases". Reason: Read timed out',
        "false",
        EXECUTION_STATE_FAILED,
    )
    siemplify.result.add_result_json.assert_not_called()
    siemplify.result.add_data_table.assert_not_called()


def test_list_cases_handles_auth_error_cleanly(sf_cls: MagicMock) -> None:
    """Authentication failures during SalesforceManager init fail cleanly."""
    sf_cls.side_effect = RuntimeError("INVALID_LOGIN")

    siemplify = run_list_cases({})

    siemplify.LOGGER.exception.assert_called_once()
    siemplify.end.assert_called_once_with(
        'Error executing action "List Cases". Reason: INVALID_LOGIN',
        "false",
        EXECUTION_STATE_FAILED,
    )
    siemplify.result.add_result_json.assert_not_called()
    siemplify.result.add_data_table.assert_not_called()
