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

"""Tests for building and submitting the Execute Simple Query SQL in SnowflakeManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ..core.SnowflakeExceptions import InvalidQueryParameterError
from ..core.SnowflakeManager import SnowflakeManager

API_ROOT: str = "https://example.snowflakecomputing.com/"
STATEMENT_HANDLE: str = "01b2c3d4-0000-1111-0000-000000000001"


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch) -> SnowflakeManager:
    """Creates a SnowflakeManager without generating a real JWT token."""
    monkeypatch.setattr(SnowflakeManager, "_generate_jwt_token", lambda _self: "token")
    return SnowflakeManager(
        api_root=API_ROOT,
        account="account",
        username="user",
        private_key_file="",
    )


@pytest.fixture
def session_request(manager: SnowflakeManager, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replaces the manager session's request method and returns the mock."""
    response: MagicMock = MagicMock()
    response.json.return_value = {"statementHandle": STATEMENT_HANDLE}
    request: MagicMock = MagicMock(return_value=response)
    monkeypatch.setattr(manager.session, "request", request)
    return request


def test_build_query_string_with_all_parameters(manager: SnowflakeManager) -> None:
    """All parameters are validated and placed in the expected query clauses."""
    query: str = manager.build_query_string(
        fields_to_return="id, name",
        table="DB.PUBLIC.USERS",
        where_filter="name = 'O''Brien'",
        sort_order="desc",
        sort_field="id",
    )

    assert query == "SELECT id, name FROM DB.PUBLIC.USERS WHERE (name = 'O''Brien') ORDER BY id DESC"


def test_build_query_string_keeps_expressions_aliases_and_multi_column_sort(manager: SnowflakeManager) -> None:
    """Expressions, aliases and several sort fields keep working as before the validation."""
    query: str = manager.build_query_string(
        fields_to_return="COUNT(*) AS total, UPPER(u.name)",
        table="users u",
        where_filter="u.active = TRUE",
        sort_order="ASC",
        sort_field="u.name DESC, u.id",
    )

    assert query == (
        "SELECT COUNT(*) AS total, UPPER(u.name) FROM users u WHERE (u.active = TRUE) ORDER BY u.name DESC, u.id ASC"
    )


def test_build_query_string_defaults(manager: SnowflakeManager) -> None:
    """Empty optional parameters produce a plain SELECT * query."""
    query: str = manager.build_query_string(
        fields_to_return="",
        table="users",
        where_filter=None,
        sort_order="ASC",
        sort_field=None,
    )

    assert query == "SELECT * FROM users"


def test_build_query_string_defaults_sort_order_to_asc(manager: SnowflakeManager) -> None:
    """A missing sort order falls back to ASC when a sort field is given."""
    query: str = manager.build_query_string(
        fields_to_return="*",
        table="users",
        where_filter="",
        sort_order=None,
        sort_field="created_at",
    )

    assert query == "SELECT * FROM users ORDER BY created_at ASC"


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("fields_to_return", "id FROM secrets --"),
        ("fields_to_return", "(SELECT password FROM secrets)"),
        ("table", "users; DROP TABLE users"),
        ("table", "users, secrets"),
        ("table", "users JOIN secrets ON users.id = secrets.id"),
        ("where_filter", "1=1; DROP TABLE users;--"),
        ("where_filter", "1=1) UNION SELECT * FROM secrets WHERE (1=1"),
        ("where_filter", "   "),
        ("sort_field", "id; DROP TABLE users"),
        ("sort_field", "(SELECT 1 FROM secrets)"),
        ("sort_order", "ASC; DROP TABLE users"),
    ],
)
def test_build_query_string_rejects_values_that_change_the_query(
    manager: SnowflakeManager,
    parameter: str,
    value: str,
) -> None:
    """A value that adds statements, comments or other tables fails before a query is built."""
    parameters: dict[str, str] = {
        "fields_to_return": "*",
        "table": "users",
        "where_filter": "id = 1",
        "sort_order": "ASC",
        "sort_field": "id",
    }
    parameters[parameter] = value

    with pytest.raises(InvalidQueryParameterError):
        manager.build_query_string(**parameters)


def test_submit_query_with_statement_count_limits_the_request_to_one_statement(
    manager: SnowflakeManager,
    session_request: MagicMock,
) -> None:
    """Execute Simple Query sends MULTI_STATEMENT_COUNT so Snowflake runs only one statement."""
    query_id: str | None = manager.submit_query(
        query="SELECT * FROM users",
        database="DB",
        schema="PUBLIC",
        limit=50,
        statement_count=1,
    )

    payload: dict[str, Any] = session_request.call_args.kwargs["json"]
    assert query_id == STATEMENT_HANDLE
    assert payload["statement"] == "SELECT * FROM users LIMIT 50"
    assert payload["parameters"] == {"MULTI_STATEMENT_COUNT": "1"}


def test_submit_query_without_statement_count_keeps_the_payload_unchanged(
    manager: SnowflakeManager,
    session_request: MagicMock,
) -> None:
    """Execute Custom Query doesn't pass a statement count, so its payload stays the same."""
    manager.submit_query(query="SHOW TABLES", database="DB", schema=None, limit=10)

    payload: dict[str, Any] = session_request.call_args.kwargs["json"]
    assert payload == {
        "statement": "SHOW TABLES LIMIT 10",
        "timeout": 300,
        "resultSetMetaData": {"format": "jsonv2"},
        "database": "DB",
    }
