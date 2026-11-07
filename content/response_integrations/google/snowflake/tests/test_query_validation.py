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
    validate_identifier,
    validate_sort_order,
    validate_where_filter,
)
from ..core.SnowflakeExceptions import InvalidQueryParameterError, SnowflakeException


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("users", "users"),
        ("  users  ", "users"),
        ("MY_DB.PUBLIC.USERS", "MY_DB.PUBLIC.USERS"),
        ("_tbl$1", "_tbl$1"),
        ('"My Table"', '"My Table"'),
        ('"db"."schema"."tab;le"', '"db"."schema"."tab;le"'),
        ('"say ""hi"""', '"say ""hi"""'),
    ],
)
def test_validate_identifier_accepts_valid_names(value: str, expected: str) -> None:
    """Valid plain, qualified and quoted names are returned stripped."""
    assert validate_identifier(value, "Table") == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "users; DROP TABLE users",
        "users WHERE 1=1",
        "users--",
        "users UNION SELECT * FROM secrets",
        "1users",
        "a.b.c.d.e",
        "users.",
        '"unclosed',
        '"a" "b"',
        "(SELECT 1)",
    ],
)
def test_validate_identifier_rejects_injection(value: str) -> None:
    """Anything that is not a plain or qualified name is rejected."""
    with pytest.raises(InvalidQueryParameterError, match='"Table"'):
        validate_identifier(value, "Table")


def test_invalid_query_parameter_error_is_snowflake_exception() -> None:
    """The new error is a SnowflakeException, so existing error handling still applies."""
    assert issubclass(InvalidQueryParameterError, SnowflakeException)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("*", "*"),
        ("id", "id"),
        ("id,name", "id, name"),
        (" id , users.name , u.* ", "id, users.name, u.*"),
        ('"First Name", email', '"First Name", email'),
    ],
)
def test_validate_fields_to_return_accepts_field_lists(value: str, expected: str) -> None:
    """Field names, "*" and "table.*" are accepted and re-joined with ", "."""
    assert validate_fields_to_return(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "id,",
        "id,,name",
        "id FROM secrets --",
        "id; DROP TABLE users",
        "(SELECT password FROM secrets)",
        "COUNT(*)",
        "id AS user_id",
    ],
)
def test_validate_fields_to_return_rejects_injection(value: str) -> None:
    """Expressions, empty items and SQL keywords are rejected."""
    with pytest.raises(InvalidQueryParameterError, match='"Fields To Return"'):
        validate_fields_to_return(value)


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
def test_validate_where_filter_rejects_injection(value: str, reason: str) -> None:
    """Statement separators, comments and unbalanced quotes or parentheses are rejected."""
    with pytest.raises(InvalidQueryParameterError, match=reason):
        validate_where_filter(value)
