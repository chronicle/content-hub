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
from unittest.mock import patch

import pytest

from salesforce.core.constants import DEFAULT_MAX_RECORDS, INVALID_MAX_RECORDS_MSG, MAX_RECORDS_LIMIT
from salesforce.core.SalesforceManager import (
    CASE_PROPERTIES,
    SalesforceManager,
    SalesforceManagerError,
)
from salesforce.core.utils import parse_max_records

if TYPE_CHECKING:
    from collections.abc import Iterator


def expected_query(literal: str) -> str:
    """Build the expected (never executed) SOQL text for a CaseNumber literal.

    Args:
        literal: The already-quoted SOQL string literal.

    Returns:
        The full query the manager is expected to send.
    """
    return " ".join(["SELECT", ", ".join(CASE_PROPERTIES), "FROM Case WHERE CaseNumber =", literal])


@pytest.fixture
def manager() -> Iterator[SalesforceManager]:
    """Build a manager whose Salesforce client is a mock returning no records."""
    with patch("salesforce.core.SalesforceManager.Salesforce") as salesforce_cls:
        salesforce_cls.return_value.query.return_value = {"records": [], "done": True}
        yield SalesforceManager("user", "pass", "token")


def sent_query(manager: SalesforceManager) -> str:
    """Return the single SOQL query sent to the mocked Salesforce client.

    Args:
        manager: Manager under test.

    Returns:
        The SOQL string passed to `sf.query`.
    """
    manager.sf.query.assert_called_once()
    return manager.sf.query.call_args.args[0]


def test_valid_case_number_builds_exact_query(manager: SalesforceManager) -> None:
    """A normal case number yields the full expected query, sent exactly once."""
    manager.sf.query.return_value = {"records": [{"Id": "500A"}], "done": True}

    manager.get_case_by_number("00001001")

    assert sent_query(manager) == expected_query("'00001001'")


def test_returns_first_record_when_multiple_match(manager: SalesforceManager) -> None:
    """Only the first returned record is handed back to the caller."""
    first: dict[str, Any] = {"Id": "500A", "CaseNumber": "00001001"}
    manager.sf.query.return_value = {"records": [first, {"Id": "500B"}], "done": True}

    assert manager.get_case_by_number("00001001") == first


def test_not_found_message_uses_trimmed_value(manager: SalesforceManager) -> None:
    """The not-found error reports the normalized case number."""
    with pytest.raises(SalesforceManagerError, match=r"^Case 00001001 was not found\.$"):
        manager.get_case_by_number("  00001001  ")


@pytest.mark.parametrize(
    ("payload", "expected_literal"),
    [
        pytest.param("1' OR Id != '", r"'1\' OR Id != \''", id="ticket-payload"),
        pytest.param(
            r"1\' OR Id != null OR CaseNumber = \'",
            r"'1\\\' OR Id != null OR CaseNumber = \\\''",
            id="backslash-bypass-of-pypika",
        ),
        pytest.param('1" OR Id != "', r"""'1\" OR Id != \"'""", id="double-quote"),
        pytest.param("1'\nOR Id != '", r"'1\'\nOR Id != \''", id="newline"),
        pytest.param("1\t\r2", r"'1\t\r2'", id="tab-and-carriage-return"),
        pytest.param("1\\", r"'1\\'", id="lone-trailing-backslash"),
        pytest.param("00001001'", r"'00001001\''", id="trailing-quote"),
        pytest.param("1' --", r"'1\' --'", id="comment-like"),
        pytest.param("%_", "'%_'", id="like-wildcards-literal"),
        pytest.param("cas\u00e9\u00d1\u2019", "'cas\u00e9\u00d1\u2019'", id="unicode"),
    ],
)
def test_special_characters_stay_inside_one_literal(
    manager: SalesforceManager, payload: str, expected_literal: str
) -> None:
    """Quotes, backslashes and control characters are SOQL-escaped, never executed."""
    with pytest.raises(SalesforceManagerError, match="was not found"):
        manager.get_case_by_number(payload)

    assert sent_query(manager) == expected_query(expected_literal)


@pytest.mark.parametrize(
    ("value", "expected_literal"),
    [
        pytest.param("  00001001  ", "'00001001'", id="surrounding-whitespace-trimmed"),
        pytest.param(1001, "'1001'", id="int-quoted-as-string"),
        pytest.param(["a", "b"], r"'[\'a\', \'b\']'", id="list-not-expanded-to-IN"),
    ],
)
def test_non_canonical_input_is_normalized_to_string_literal(
    manager: SalesforceManager, value: object, expected_literal: str
) -> None:
    """Whitespace is trimmed and non-string values become one quoted string."""
    with pytest.raises(SalesforceManagerError, match="was not found"):
        manager.get_case_by_number(value)

    assert sent_query(manager) == expected_query(expected_literal)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
        pytest.param("\t\n", id="whitespace-control-chars"),
        pytest.param(None, id="none"),
        pytest.param(0, id="zero-is-falsy"),
        pytest.param(False, id="false-is-falsy"),
    ],
)
def test_empty_input_rejected_before_any_query(manager: SalesforceManager, value: object) -> None:
    """Empty or falsy input fails fast and never reaches Salesforce."""
    with pytest.raises(SalesforceManagerError, match=r"^Case Number cannot be empty\.$"):
        manager.get_case_by_number(value)

    manager.sf.query.assert_not_called()


def test_salesforce_client_error_propagates(manager: SalesforceManager) -> None:
    """Errors raised by the Salesforce client are not swallowed."""
    manager.sf.query.side_effect = RuntimeError("MALFORMED_QUERY")

    with pytest.raises(RuntimeError, match="MALFORMED_QUERY"):
        manager.get_case_by_number("00001001")


def test_get_case_by_id_builds_quoted_query(manager: SalesforceManager) -> None:
    """get_case_by_id quotes the Id the same way as the CaseNumber lookup."""
    record: dict[str, Any] = {"Id": "500A", "CaseNumber": "00001001"}
    manager.sf.query.return_value = {"records": [record], "done": True}

    assert manager.get_case_by_id("500A") == record
    assert sent_query(manager) == " ".join(["SELECT", ", ".join(CASE_PROPERTIES), "FROM Case WHERE Id =", "'500A'"])


def test_create_case_fetches_new_case_by_id(manager: SalesforceManager) -> None:
    """create_case looks up the new case using the Id returned by Salesforce."""
    record: dict[str, Any] = {"Id": "500NEW", "CaseNumber": "00001002"}
    manager.sf.Case.create.return_value = {"success": True, "id": "500NEW"}
    manager.sf.query.return_value = {"records": [record], "done": True}

    assert manager.create_case(subject="Test") == record
    assert sent_query(manager).endswith("WHERE Id = '500NEW'")


def test_connectivity_executes_single_row_case_id_query(manager: SalesforceManager) -> None:
    """test_connectivity runs SELECT Id FROM Case LIMIT 1 and never calls query_more."""
    manager.sf.query.return_value = {"records": [{"Id": "500A"}], "done": True}

    assert manager.test_connectivity() is True
    assert sent_query(manager) == "SELECT Id FROM Case LIMIT 1"
    manager.sf.query_more.assert_not_called()


def test_get_cases_uses_default_limit_and_descending_order(manager: SalesforceManager) -> None:
    """get_cases() defaults to DEFAULT_MAX_RECORDS ordered by CreatedDate DESC."""
    record: dict[str, Any] = {
        "Id": "500A",
        "CaseNumber": "00001001",
        "attributes": {"type": "Case", "url": "/services/data/v64.0/sobjects/Case/500A"},
    }
    manager.sf.query.return_value = {"records": [record], "done": True}

    cases = manager.get_cases()

    expected = f"SELECT {', '.join(CASE_PROPERTIES)} FROM Case ORDER BY CreatedDate DESC LIMIT {DEFAULT_MAX_RECORDS}"
    assert sent_query(manager) == expected
    assert cases == [{"Id": "500A", "CaseNumber": "00001001"}]


@pytest.mark.parametrize(
    ("raw_limit", "expected_limit"),
    [
        pytest.param(None, DEFAULT_MAX_RECORDS, id="none-uses-default"),
        pytest.param("", DEFAULT_MAX_RECORDS, id="empty-string-uses-default"),
        pytest.param("   ", DEFAULT_MAX_RECORDS, id="whitespace-uses-default"),
        pytest.param("1", 1, id="minimum-str"),
        pytest.param("25", 25, id="numeric-string"),
        pytest.param("  100  ", 100, id="padded-numeric-string"),
        pytest.param(str(MAX_RECORDS_LIMIT), MAX_RECORDS_LIMIT, id="maximum-str"),
    ],
)
def test_parse_max_records_accepts_valid_inputs(raw_limit: str | None, expected_limit: int) -> None:
    """Valid string/None inputs normalize to a positive integer within [1, MAX_RECORDS_LIMIT]."""
    assert parse_max_records(raw_limit) == expected_limit


@pytest.mark.parametrize(
    "invalid_raw",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative-str"),
        pytest.param(str(MAX_RECORDS_LIMIT + 1), id="above-max-str"),
        pytest.param("abc", id="non-numeric-str"),
        pytest.param("10.5", id="float-str"),
    ],
)
def test_parse_max_records_rejects_invalid_inputs(invalid_raw: str) -> None:
    """Invalid string inputs raise SalesforceManagerError with INVALID_MAX_RECORDS_MSG."""
    with pytest.raises(SalesforceManagerError) as exc_info:
        parse_max_records(invalid_raw)

    assert str(exc_info.value) == INVALID_MAX_RECORDS_MSG


@pytest.mark.parametrize(
    "invalid_limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-5, id="negative-int"),
        pytest.param(MAX_RECORDS_LIMIT + 1, id="above-max-int"),
    ],
)
def test_get_cases_rejects_invalid_max_records_before_query(manager: SalesforceManager, invalid_limit: int) -> None:
    """Out-of-range max_records raises SalesforceManagerError without querying Salesforce."""
    with pytest.raises(SalesforceManagerError) as exc_info:
        manager.get_cases(max_records=invalid_limit)

    assert str(exc_info.value) == INVALID_MAX_RECORDS_MSG
    manager.sf.query.assert_not_called()


def test_run_query_stops_pagination_once_max_records_reached(manager: SalesforceManager) -> None:
    """run_query halts query_more as soon as max_records items are collected and slices excess."""
    manager.sf.query.return_value = {
        "records": [{"Id": "500A"}, {"Id": "500B"}],
        "done": False,
        "nextRecordsUrl": "/services/data/v64.0/query/page-2",
    }
    manager.sf.query_more.side_effect = [
        {
            "records": [{"Id": "500C"}, {"Id": "500D"}],
            "done": False,
            "nextRecordsUrl": "/services/data/v64.0/query/page-3",
        },
        {
            "records": [{"Id": "500E"}],
            "done": True,
        },
    ]

    records = manager.run_query("SELECT Id FROM Case", max_records=3)

    assert records == [{"Id": "500A"}, {"Id": "500B"}, {"Id": "500C"}]
    manager.sf.query_more.assert_called_once_with("/services/data/v64.0/query/page-2", True)


def test_run_query_breaks_safely_when_next_records_url_missing(manager: SalesforceManager) -> None:
    """Malformed pagination responses missing nextRecordsUrl do not loop infinitely."""
    manager.sf.query.return_value = {"records": [{"Id": "500A"}], "done": False}

    assert manager.run_query("SELECT Id FROM Case") == [{"Id": "500A"}]
    manager.sf.query_more.assert_not_called()
