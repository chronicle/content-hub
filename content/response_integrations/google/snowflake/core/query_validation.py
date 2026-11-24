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

"""Validation of user-provided values used to build Snowflake SQL queries.

Every Execute Simple Query parameter that is placed in the SQL text is checked first, so a
value that comes from alert data can't add statements or comments to the query and can't make
it read from other tables:

- Table: a table name, optionally qualified with the database and schema or quoted, with an
  optional alias.
- Fields To Return and Sort Field: column expressions, such as "id, name", "COUNT(*)",
  "id AS user_id" or "name DESC, id", without subqueries or references to other tables.
- Where Filter: a condition that stays inside the WHERE clause.
- Sort Order: ASC or DESC.

Text inside single-quoted strings and double-quoted identifiers is not checked. Outside of it,
statement separators, comment markers and dollar-quoted strings are not allowed, and quotes and
parentheses must be balanced.
"""

from __future__ import annotations

import re

from .constants import ASC_SORT_ORDER, SORT_ORDERS
from .SnowflakeExceptions import InvalidQueryParameterError

TABLE_PARAMETER: str = "Table"
FIELDS_TO_RETURN_PARAMETER: str = "Fields To Return"
SORT_FIELD_PARAMETER: str = "Sort Field"
SORT_ORDER_PARAMETER: str = "Sort Order"
WHERE_FILTER_PARAMETER: str = "Where Filter"

UNQUOTED_IDENTIFIER: str = r"[A-Za-z_][A-Za-z0-9_$]*"
QUOTED_IDENTIFIER: str = r'"(?:[^"]|"")+"'
IDENTIFIER: str = rf"(?:{UNQUOTED_IDENTIFIER}|{QUOTED_IDENTIFIER})"
TABLE_NAME: str = rf"{IDENTIFIER}(?:\.{IDENTIFIER}){{0,2}}|{IDENTIFIER}\.\.{IDENTIFIER}"
TABLE_ALIAS: str = rf"(?!AS(?![A-Za-z0-9_$])){IDENTIFIER}"
TABLE_WITH_OPTIONAL_ALIAS_PATTERN: re.Pattern[str] = re.compile(
    rf"(?:{TABLE_NAME})(?:\s+(?:AS\s+)?{TABLE_ALIAS})?",
    re.IGNORECASE,
)
QUOTED_TEXT_PATTERN: re.Pattern[str] = re.compile(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"]|\"\")*\"", re.DOTALL)
SQL_WORD_PATTERN: re.Pattern[str] = re.compile(
    r"\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z0-9_$]*",
)
STATEMENT_OR_COMMENT_MARKERS: tuple[str, ...] = (";", "--", "//", "/*", "*/", "$$")
TABLE_ACCESS_KEYWORDS: frozenset[str] = frozenset(
    {"FROM", "INTERSECT", "JOIN", "LATERAL", "MINUS", "SELECT", "TABLE", "UNION"},
)


def validate_table(table: str) -> str:
    """Validate the Table parameter.

    Args:
        table: A table name, e.g. "users", "DB.PUBLIC.USERS" or '"My Table"', with an optional
            alias, e.g. "users u" or "users AS u".

    Returns:
        The table without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the value is not a table name with an optional alias.

    """
    stripped_table: str = table.strip()
    is_table_name: bool = TABLE_WITH_OPTIONAL_ALIAS_PATTERN.fullmatch(stripped_table) is not None
    if not is_table_name or _has_table_access_keyword(stripped_table):
        msg: str = (
            f'Invalid value was provided for "{TABLE_PARAMETER}": {table}. '
            "Only a table name with an optional alias is allowed."
        )
        raise InvalidQueryParameterError(msg)

    return stripped_table


def validate_fields_to_return(fields_to_return: str) -> str:
    """Validate the Fields To Return parameter.

    Args:
        fields_to_return: Column expressions, e.g. "*", "id, name", "COUNT(*)" or "id AS user_id".

    Returns:
        The fields without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the fields contain a subquery, a reference to another
            table, a statement separator or a comment.

    """
    stripped_fields: str = fields_to_return.strip()
    reason: str | None = _get_column_expressions_violation(stripped_fields)
    if reason:
        msg: str = _build_invalid_value_message(FIELDS_TO_RETURN_PARAMETER, fields_to_return, reason)
        raise InvalidQueryParameterError(msg)

    return stripped_fields


def validate_sort_field(sort_field: str) -> str:
    """Validate the Sort Field parameter.

    Args:
        sort_field: Column expressions to sort by, e.g. "created_at" or "name DESC, id".

    Returns:
        The sort field without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the sort field contains a subquery, a reference to
            another table, a statement separator or a comment.

    """
    stripped_sort_field: str = sort_field.strip()
    reason: str | None = _get_column_expressions_violation(stripped_sort_field)
    if reason:
        msg: str = _build_invalid_value_message(SORT_FIELD_PARAMETER, sort_field, reason)
        raise InvalidQueryParameterError(msg)

    return stripped_sort_field


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
        msg: str = f'Invalid value was provided for "{SORT_ORDER_PARAMETER}": {sort_order}. Possible values: ASC, DESC.'
        raise InvalidQueryParameterError(msg)

    return normalized


def validate_where_filter(where_filter: str) -> str:
    """Validate that the WHERE filter is a single condition that can't escape the WHERE clause.

    Args:
        where_filter: The WHERE condition, without the WHERE keyword.

    Returns:
        The filter without surrounding whitespace.

    Raises:
        InvalidQueryParameterError: If the filter is not allowed.

    """
    stripped_filter: str = where_filter.strip()
    reason: str | None = _get_structure_violation(stripped_filter)
    if reason:
        msg: str = _build_invalid_value_message(WHERE_FILTER_PARAMETER, where_filter, reason)
        raise InvalidQueryParameterError(msg)

    return stripped_filter


def _get_column_expressions_violation(stripped_value: str) -> str | None:
    """Find why column expressions can't be placed in the SELECT or ORDER BY clause.

    Args:
        stripped_value: The column expressions without surrounding whitespace.

    Returns:
        The reason the value is not allowed, or None if it is allowed.

    """
    reason: str | None = _get_structure_violation(stripped_value)
    if reason:
        return reason

    if _has_table_access_keyword(stripped_value):
        return "subqueries and references to other tables are not allowed"

    return None


def _get_structure_violation(stripped_value: str) -> str | None:
    """Find why a value could end the query clause it is placed in.

    Args:
        stripped_value: The value without surrounding whitespace.

    Returns:
        The reason the value is not allowed, or None if it is allowed.

    """
    if not stripped_value:
        return "it is empty"

    unquoted_value: str = _remove_quoted_text(stripped_value)
    if "'" in unquoted_value or '"' in unquoted_value:
        return "it has an unclosed quote"

    if any(marker in unquoted_value for marker in STATEMENT_OR_COMMENT_MARKERS):
        return "semicolons, comments and $$ are not allowed"

    if not _has_balanced_parentheses(unquoted_value):
        return "its parentheses are not balanced"

    return None


def _has_table_access_keyword(value: str) -> bool:
    """Check whether a value uses a keyword that starts a subquery or references another table.

    Args:
        value: The value to check. Quoted text is ignored.

    Returns:
        True if the value contains one of the table access keywords, otherwise False.

    """
    words: list[str] = SQL_WORD_PATTERN.findall(_remove_quoted_text(value))
    return any(word.upper() in TABLE_ACCESS_KEYWORDS for word in words)


def _remove_quoted_text(value: str) -> str:
    """Replace string literals and quoted identifiers with a space.

    Args:
        value: The value to clean.

    Returns:
        The value without quoted text.

    """
    return QUOTED_TEXT_PATTERN.sub(" ", value)


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


def _build_invalid_value_message(parameter_name: str, value: str, reason: str) -> str:
    """Build the error message for a value that can't be used in the query.

    Args:
        parameter_name: The action parameter name.
        value: The value that was provided.
        reason: Why the value is not allowed.

    Returns:
        The error message.

    """
    return f'Invalid value was provided for "{parameter_name}": {value}. Reason: {reason}.'
