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

"""Tests for building the Execute Simple Query SQL in SnowflakeManager."""

from __future__ import annotations

import pytest

from ..core.SnowflakeExceptions import InvalidQueryParameterError
from ..core.SnowflakeManager import SnowflakeManager


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch) -> SnowflakeManager:
    """Creates a SnowflakeManager without generating a real JWT token."""
    monkeypatch.setattr(SnowflakeManager, "_generate_jwt_token", lambda _self: "token")
    return SnowflakeManager(
        api_root="https://example.snowflakecomputing.com/",
        account="account",
        username="user",
        private_key_file="",
    )


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
        ("table", "users; DROP TABLE users"),
        ("where_filter", "1=1; DROP TABLE users;--"),
        ("where_filter", "1=1) UNION SELECT * FROM secrets WHERE (1=1"),
        ("where_filter", "   "),
        ("sort_field", "id; DROP TABLE users"),
        ("sort_order", "ASC; DROP TABLE users"),
    ],
)
def test_build_query_string_rejects_injection(manager: SnowflakeManager, parameter: str, value: str) -> None:
    """An injection payload in any parameter fails before a query is built."""
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
