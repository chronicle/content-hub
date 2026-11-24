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

"""Tests for validating user-provided values used in Snowflake SQL queries."""

from __future__ import annotations

import pytest

from ..core.query_validation import (
    validate_fields_to_return,
    validate_sort_field,
    validate_sort_order,
    validate_table,
    validate_where_filter,
)
from ..core.SnowflakeExceptions import InvalidQueryParameterError, SnowflakeException


def test_invalid_query_parameter_error_is_snowflake_exception() -> None:
    """The new error is a SnowflakeException, so existing error handling still applies."""
    assert issubclass(InvalidQueryParameterError, SnowflakeException)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("users", "users"),
        ("  users  ", "users"),
        ("MY_DB.PUBLIC.USERS", "MY_DB.PUBLIC.USERS"),
        ("MY_DB..USERS", "MY_DB..USERS"),
        ("_tbl$1", "_tbl$1"),
        ('"My Table"', '"My Table"'),
        ('"db"."schema"."tab;le"', '"db"."schema"."tab;le"'),
        ('"say ""hi"""', '"say ""hi"""'),
        ('"select"', '"select"'),
        ("users u", "users u"),
        ("users AS u", "users AS u"),
        ('PUBLIC.USERS as "User Alias"', 'PUBLIC.USERS as "User Alias"'),
        ("users asset", "users asset"),
    ],
)
def test_validate_table_accepts_table_names_with_optional_alias(value: str, expected: str) -> None:
    """Plain, qualified and quoted table names, with or without an alias, are returned stripped."""
    assert validate_table(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "users; DROP TABLE users",
        "users WHERE 1=1",
        "users--",
        "users UNION SELECT * FROM secrets",
        "users, secrets",
        "users JOIN secrets ON users.id = secrets.id",
        "users JOIN",
        "users AS",
        "users u extra",
        "1users",
        "a.b.c.d",
        "users.",
        '"unclosed',
        "(SELECT 1)",
        "TABLE(RESULT_SCAN(LAST_QUERY_ID()))",
    ],
)
def test_validate_table_rejects_other_values(value: str) -> None:
    """Joins, extra tables, subqueries, statements and invalid names are rejected."""
    with pytest.raises(InvalidQueryParameterError, match="Only a table name with an optional alias is allowed"):
        validate_table(value)


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "id",
        "id,name",
        "id , users.name , u.*",
        '"First Name", email',
        "COUNT(*)",
        "id AS user_id",
        "UPPER(name)",
        "DISTINCT name",
        "COUNT(DISTINCT id), MAX(created_at) AS last_seen",
        "price * quantity AS total",
        "raw:user::string AS user_name",
        "'from' AS source, \"SELECT\"",
        "updated_from, selected, table_name, col1from",
    ],
)
def test_validate_fields_to_return_accepts_column_expressions(value: str) -> None:
    """Column names, wildcards, functions, aliases and expressions are accepted."""
    assert validate_fields_to_return(f"  {value}  ") == value


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("id FROM secrets --", "semicolons"),
        ("id; DROP TABLE users", "semicolons"),
        ("(SELECT password FROM secrets)", "subqueries"),
        ("* FROM secrets UNION SELECT *", "subqueries"),
        ("id FROM secrets", "subqueries"),
        ("1from secrets", "subqueries"),
        ("1e5from secrets", "subqueries"),
        ("id, (select max(id) from secrets)", "subqueries"),
        ("a INTERSECT b", "subqueries"),
        ("a MINUS b", "subqueries"),
        ("value FROM LATERAL FLATTEN(input => data)", "subqueries"),
        ("COUNT(*", "parentheses"),
        ("name = 'unclosed", "unclosed quote"),
        ("$$x$$", "semicolons"),
        ("   ", "it is empty"),
    ],
)
def test_validate_fields_to_return_rejects_other_values(value: str, reason: str) -> None:
    """Subqueries, other tables, statement separators, comments and unbalanced values are rejected."""
    with pytest.raises(InvalidQueryParameterError, match=f'"Fields To Return".*{reason}'):
        validate_fields_to_return(value)


@pytest.mark.parametrize(
    "value",
    ["created_at", "name, id", "name DESC, id", "t.created_at", '"Created At"', "LOWER(name)", "1"],
)
def test_validate_sort_field_accepts_column_expressions(value: str) -> None:
    """One or more column expressions, with optional directions, are accepted."""
    assert validate_sort_field(f" {value} ") == value


@pytest.mark.parametrize(
    "value",
    [
        "id; DROP TABLE users",
        "id --",
        "(SELECT 1 FROM secrets)",
        "id) UNION (SELECT 1",
        "id UNION SELECT id FROM secrets",
        "",
    ],
)
def test_validate_sort_field_rejects_other_values(value: str) -> None:
    """Subqueries, statement separators, comments and empty values are rejected."""
    with pytest.raises(InvalidQueryParameterError, match='"Sort Field"'):
        validate_sort_field(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "ASC"),
        ("", "ASC"),
        ("ASC", "ASC"),
        ("desc", "DESC"),
        (" Desc ", "DESC"),
    ],
)
def test_validate_sort_order_accepts_asc_and_desc(value: str | None, expected: str) -> None:
    """Only ASC and DESC are accepted, case-insensitively; empty values default to ASC."""
    assert validate_sort_order(value) == expected


@pytest.mark.parametrize("value", ["ASC; DROP TABLE users", "DESC --", "RANDOM()", "UP"])
def test_validate_sort_order_rejects_other_values(value: str) -> None:
    """Any other sort order value is rejected."""
    with pytest.raises(InvalidQueryParameterError, match='"Sort Order"'):
        validate_sort_order(value)


@pytest.mark.parametrize(
    "value",
    [
        "id = 1",
        "name = 'O''Brien'",
        r"name = 'it\'s'",
        "name = 'a; b -- c /* d */ $$ e'",
        "note = 'unbalanced ( in a string'",
        "\"Full Name\" = 'x'",
        "(status = 'open' OR status = 'new') AND severity > 3",
        "id IN (SELECT id FROM allowed_ids)",
        "price > $1",
    ],
)
def test_validate_where_filter_accepts_single_conditions(value: str) -> None:
    """Normal conditions are accepted, including special characters inside quotes."""
    assert validate_where_filter(f"  {value}  ") == value


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("1=1; DROP TABLE users;--", "semicolons"),
        ("1=1 -- comment", "semicolons"),
        ("1=1 // comment", "semicolons"),
        ("1=1 /* comment */", "semicolons"),
        ("name = $$x$$", "semicolons"),
        ("1=1) UNION SELECT * FROM secrets WHERE (1=1", "parentheses"),
        ("(1=1", "parentheses"),
        ("name = 'unclosed", "unclosed quote"),
        (r"name = 'escaped\' ; DROP TABLE users", "unclosed quote"),
        ('"Full Name = 1', "unclosed quote"),
        ("", "it is empty"),
        ("   ", "it is empty"),
    ],
)
def test_validate_where_filter_rejects_values_that_leave_the_where_clause(value: str, reason: str) -> None:
    """Statement separators, comments and unbalanced quotes or parentheses are rejected."""
    with pytest.raises(InvalidQueryParameterError, match=reason):
        validate_where_filter(value)
