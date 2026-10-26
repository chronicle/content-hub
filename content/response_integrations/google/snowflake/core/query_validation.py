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

"""Validation of user-provided values used to build Snowflake SQL queries."""

from __future__ import annotations

import re

from .constants import ALL_FIELDS_WILDCARD, ASC_SORT_ORDER, SORT_ORDERS
from .SnowflakeExceptions import InvalidQueryParameterError

_UNQUOTED_IDENTIFIER: str = r"[A-Za-z_][A-Za-z0-9_$]*"
_QUOTED_IDENTIFIER: str = r'"(?:[^"]|"")+"'
_IDENTIFIER_PART: str = rf"(?:{_UNQUOTED_IDENTIFIER}|{_QUOTED_IDENTIFIER})"

# A name with up to 4 dot-separated parts, e.g. "table", "schema.table" or "db.schema.table.column".
_QUALIFIED_IDENTIFIER: re.Pattern[str] = re.compile(rf"{_IDENTIFIER_PART}(?:\.{_IDENTIFIER_PART}){{0,3}}")

# Same as above, optionally ending with ".*", e.g. "table.*".
_FIELD: re.Pattern[str] = re.compile(rf"{_IDENTIFIER_PART}(?:\.{_IDENTIFIER_PART}){{0,3}}(?:\.\*)?")

# String literals ('...' with '' or backslash escapes) and quoted identifiers ("..." with "" escapes).
_QUOTED_TEXT: re.Pattern[str] = re.compile(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"]|\"\")*\"", re.DOTALL)

# Statement separators, comment markers and dollar-quoted strings are not allowed outside quotes.
_FORBIDDEN_FILTER_TOKENS: tuple[str, ...] = (";", "--", "//", "/*", "*/", "$$")


def validate_identifier(value: str, param_name: str) -> str:
    """Validate that a value is a plain or qualified Snowflake identifier.

    Args:
        value: The identifier to validate, e.g. a table or column name.
        param_name: The action parameter name, used in the error message.

    Returns:
        The identifier without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the value is not a valid identifier.

    """
    identifier: str = value.strip()
    if not _QUALIFIED_IDENTIFIER.fullmatch(identifier):
        msg: str = f'Invalid value was provided for "{param_name}": {value}. Only a table or column name is allowed.'
        raise InvalidQueryParameterError(msg)

    return identifier


def validate_fields_to_return(fields_to_return: str) -> str:
    """Validate a comma-separated list of fields to return.

    Args:
        fields_to_return: Comma-separated field names. "*" and "table.*" are allowed.

    Returns:
        The fields joined with ", ".

    Raises:
        InvalidQueryParameterError: If any of the fields is not a valid field name.

    """
    fields: list[str] = [field.strip() for field in fields_to_return.split(",")]
    for field in fields:
        if field != ALL_FIELDS_WILDCARD and not _FIELD.fullmatch(field):
            msg: str = (
                f'Invalid value was provided for "Fields To Return": {fields_to_return}. '
                "Only comma-separated field names are allowed."
            )
            raise InvalidQueryParameterError(msg)

    return ", ".join(fields)


def validate_sort_order(sort_order: str | None) -> str:
    """Validate the sort order.

    Args:
        sort_order: The sort order. Empty values default to ASC.

    Returns:
        The sort order in upper case.

    Raises:
        InvalidQueryParameterError: If the sort order is not ASC or DESC.

    """
    if not sort_order:
        return ASC_SORT_ORDER

    normalized: str = sort_order.strip().upper()
    if normalized not in SORT_ORDERS:
        msg: str = f'Invalid value was provided for "Sort Order": {sort_order}. Possible values: ASC, DESC.'
        raise InvalidQueryParameterError(msg)

    return normalized


def validate_where_filter(where_filter: str) -> str:
    """Validate that the WHERE filter is a single condition that can't escape the WHERE clause.

    Quoted text is ignored. Outside of it the filter must not contain statement
    separators, comments or dollar-quoted strings, and its parentheses must be balanced.

    Args:
        where_filter: The WHERE condition, without the WHERE keyword.

    Returns:
        The filter without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the filter is not allowed.

    """
    stripped_filter: str = where_filter.strip()
    reason: str | None = _get_where_filter_violation(stripped_filter)
    if reason:
        msg: str = f'Invalid value was provided for "Where Filter": {where_filter}. Reason: {reason}.'
        raise InvalidQueryParameterError(msg)

    return stripped_filter


def _get_where_filter_violation(stripped_filter: str) -> str | None:
    """Find why a WHERE filter is not allowed.

    Args:
        stripped_filter: The filter without surrounding whitespace.

    Returns:
        The reason the filter is not allowed, or None if it is allowed.

    """
    if not stripped_filter:
        return "it is empty"

    unquoted: str = _QUOTED_TEXT.sub(" ", stripped_filter)
    if "'" in unquoted or '"' in unquoted:
        return "it has an unclosed quote"

    if any(token in unquoted for token in _FORBIDDEN_FILTER_TOKENS):
        return "semicolons, comments and $$ are not allowed"

    if not _has_balanced_parentheses(unquoted):
        return "its parentheses are not balanced"

    return None


def _has_balanced_parentheses(text: str) -> bool:
    """Check that every closing parenthesis matches an earlier opening one.

    Args:
        text: The text to check.

    Returns:
        True if the parentheses are balanced, otherwise False.

    """
    depth: int = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False

    return depth == 0
