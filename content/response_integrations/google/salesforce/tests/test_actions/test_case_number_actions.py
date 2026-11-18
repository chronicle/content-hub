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
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED

from salesforce.actions import AddComment, CloseCase, GetCase, UpdateCase

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType

CONFIG: dict[str, str] = {
    "Api Root": "https://example.my.salesforce.com",
    "Username": "user",
    "Password": "pass",
    "Token": "token",
    "Verify SSL": "false",
}
TICKET_PAYLOAD: str = "1' OR Id != '"
BYPASS_PAYLOAD: str = r"1\' OR Id != null OR CaseNumber = \'"


@pytest.fixture
def sf_client() -> Iterator[MagicMock]:
    """Mock the Salesforce client used by the real SalesforceManager (no records by default)."""
    with patch("salesforce.core.SalesforceManager.Salesforce") as salesforce_cls:
        client: MagicMock = salesforce_cls.return_value
        client.query.return_value = {"records": [], "done": True}
        yield client


def run_action(module: ModuleType, parameters: dict[str, str]) -> MagicMock:
    """Run an action's main() with a mocked SiemplifyAction.

    Args:
        module: Action module exposing `main` and `SiemplifyAction`.
        parameters: Action parameters to expose on the mocked SiemplifyAction.

    Returns:
        The mocked SiemplifyAction instance used by the action.
    """
    with patch.object(module, "SiemplifyAction") as action_cls:
        siemplify: MagicMock = action_cls.return_value
        siemplify.get_configuration.return_value = CONFIG
        siemplify.parameters = parameters
        module.main()
    return siemplify


def test_get_case_empty_number_ends_failed_without_query(sf_client: MagicMock) -> None:
    """Get Case reports a clean failure for empty input and never queries Salesforce."""
    siemplify = run_action(GetCase, {"Case Number": ""})

    siemplify.end.assert_called_once_with(
        'Error executing action "Get Case". Reason: Case Number cannot be empty.', "false", EXECUTION_STATE_FAILED
    )
    siemplify.result.add_result_json.assert_not_called()
    siemplify.result.add_json.assert_not_called()
    sf_client.query.assert_not_called()


@pytest.mark.parametrize("payload", [TICKET_PAYLOAD, BYPASS_PAYLOAD])
def test_get_case_injection_payload_returns_no_case(sf_client: MagicMock, payload: str) -> None:
    """Ticket scenario: an injection payload finds nothing instead of the first case."""
    siemplify = run_action(GetCase, {"Case Number": payload})

    siemplify.end.assert_called_once_with(
        f'Error executing action "Get Case". Reason: Case {payload} was not found.', "false", EXECUTION_STATE_FAILED
    )
    siemplify.result.add_result_json.assert_not_called()
    siemplify.result.add_json.assert_not_called()
    sf_client.query.assert_called_once()


def test_get_case_valid_number_returns_case(sf_client: MagicMock) -> None:
    """A valid case number returns the case JSON and ends successfully."""
    record: dict[str, str] = {"Id": "500A", "CaseNumber": "00001001"}
    sf_client.query.return_value = {"records": [record], "done": True}

    siemplify = run_action(GetCase, {"Case Number": "00001001"})

    siemplify.result.add_json.assert_called_once_with("Case 00001001", json.dumps(record))
    siemplify.result.add_result_json.assert_called_once_with(record)
    siemplify.end.assert_called_once_with("Successfully fetched case 00001001.", "true")


@pytest.mark.parametrize(
    ("module", "action_name", "parameters"),
    [
        pytest.param(CloseCase, "Close Case", {"Case Number": TICKET_PAYLOAD}, id="close-case"),
        pytest.param(
            AddComment,
            "Add Comment",
            {"Case Number": TICKET_PAYLOAD, "Title": "t", "Body": "b"},
            id="add-comment",
        ),
        pytest.param(
            UpdateCase,
            "Update Case",
            {"Case Number": TICKET_PAYLOAD, "Subject": "pwned", "Status": "Closed"},
            id="update-case",
        ),
    ],
)
def test_write_actions_never_modify_a_case_on_injection(
    sf_client: MagicMock, module: ModuleType, action_name: str, parameters: dict[str, str]
) -> None:
    """Write actions sharing get_case_by_number fail cleanly before any write call."""
    siemplify = run_action(module, parameters)

    siemplify.end.assert_called_once_with(
        f'Error executing action "{action_name}". Reason: Case {TICKET_PAYLOAD} was not found.',
        "false",
        EXECUTION_STATE_FAILED,
    )
    called: set[str] = {name for name, _args, _kwargs in sf_client.mock_calls if name}
    assert called == {"query"}
