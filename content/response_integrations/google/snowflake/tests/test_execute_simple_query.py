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

"""Tests for the Execute Simple Query action."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..actions import ExecuteSimpleQuery
from ..core.SnowflakeManager import SnowflakeManager

STATEMENT_HANDLE: str = "01b2c3d4-0000-1111-0000-000000000001"
INTEGRATION_CONFIGURATION: dict[str, Any] = {
    "API Root": "https://example.snowflakecomputing.com/",
    "Account": "account",
    "Username": "user",
    "Private Key": "",
    "Verify SSL": True,
}
VALID_ACTION_PARAMETERS: dict[str, Any] = {
    "Database": "DB",
    "Table": "users u",
    "Schema": "PUBLIC",
    "Where Filter": "u.name = 'alice'",
    "Fields To Return": "COUNT(*) AS total",
    "Sort Field": "total",
    "Sort Order": "DESC",
    "Max Results To Return": 50,
}


@pytest.fixture
def siemplify(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replaces the SiemplifyAction used by the action and skips the JWT key handling."""
    siemplify_action: MagicMock = MagicMock()
    monkeypatch.setattr(ExecuteSimpleQuery, "SiemplifyAction", MagicMock(return_value=siemplify_action))
    monkeypatch.setattr(SnowflakeManager, "_generate_jwt_token", lambda _self: "token")
    return siemplify_action


@pytest.fixture
def session_request(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Intercepts every HTTP request and answers like the Snowflake SQL API."""
    request: MagicMock = MagicMock(side_effect=_answer_like_snowflake)
    monkeypatch.setattr(requests.Session, "request", request)
    return request


def _answer_like_snowflake(method: str, url: str, **kwargs: object) -> MagicMock:
    """Return a finished statement with one row for any Snowflake SQL API request."""
    response: MagicMock = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "statementHandle": STATEMENT_HANDLE,
        "resultSetMetaData": {"rowType": [{"name": "TOTAL"}]},
        "data": [["1"]],
    }
    return response


def _use_action_parameters(monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any]) -> None:
    """Make the action read the valid parameters with the given overrides."""
    action_parameters: dict[str, Any] = {**VALID_ACTION_PARAMETERS, **overrides}

    def extract_action_param(
        siemplify: object = None,
        param_name: str = "",
        default_value: object = None,
        **_: object,
    ) -> object:
        return action_parameters.get(param_name, default_value)

    def extract_configuration_param(
        siemplify: object = None,
        provider_name: str = "",
        param_name: str = "",
        default_value: object = None,
        **_: object,
    ) -> object:
        return INTEGRATION_CONFIGURATION.get(param_name, default_value)

    monkeypatch.setattr(ExecuteSimpleQuery, "extract_action_param", extract_action_param)
    monkeypatch.setattr(ExecuteSimpleQuery, "extract_configuration_param", extract_configuration_param)


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("Table", "users, secrets"),
        ("Table", "users JOIN secrets ON users.id = secrets.id"),
        ("Where Filter", "1=1; DROP TABLE users;--"),
        ("Where Filter", "1=1) UNION SELECT * FROM secrets WHERE (1=1"),
        ("Fields To Return", "(SELECT password FROM secrets)"),
        ("Sort Field", "id UNION SELECT id FROM secrets"),
        ("Sort Order", "ASC; DROP TABLE users"),
    ],
)
def test_execute_simple_query_fails_without_sending_a_request_for_values_that_change_the_query(
    monkeypatch: pytest.MonkeyPatch,
    siemplify: MagicMock,
    session_request: MagicMock,
    parameter: str,
    value: str,
) -> None:
    """The action fails with a clear message and never calls Snowflake when a value can't be used."""
    _use_action_parameters(monkeypatch, {parameter: value})

    ExecuteSimpleQuery.main(True)

    output_message, result_value, status = siemplify.end.call_args.args
    assert f'Invalid value was provided for "{parameter}"' in output_message
    assert result_value is False
    assert status == EXECUTION_STATE_FAILED
    session_request.assert_not_called()


def test_execute_simple_query_submits_one_statement_with_expressions_and_aliases(
    monkeypatch: pytest.MonkeyPatch,
    siemplify: MagicMock,
    session_request: MagicMock,
) -> None:
    """Valid parameters, including expressions and aliases, are sent as a single statement."""
    _use_action_parameters(monkeypatch, {})

    ExecuteSimpleQuery.main(True)

    method, _url = session_request.call_args_list[0].args
    payload: dict[str, Any] = session_request.call_args_list[0].kwargs["json"]
    assert method == "POST"
    assert payload["statement"] == (
        "SELECT COUNT(*) AS total FROM users u WHERE (u.name = 'alice') ORDER BY total DESC LIMIT 50"
    )
    assert payload["parameters"] == {"MULTI_STATEMENT_COUNT": "1"}
    assert siemplify.end.call_args.args[2] == EXECUTION_STATE_COMPLETED
