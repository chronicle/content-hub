# Copyright 2025 Google LLC
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

"""Unit tests for the AuthenticationResults normalization helpers."""

from __future__ import annotations

from ..core import AuthenticationResults

# One combined header (Google style) plus a Postfix host that split the checks
# across separate milter headers.
COMBINED = {
    "server": "mx.google.com",
    "spf": {"result": "pass"},
    "dkim": {"result": "pass"},
    "dmarc": {"result": "pass"},
}
SPLIT = [
    {"server": "mx.google.com", "spf": {"result": "pass"}, "dkim": {"result": "fail"}},
    {"server": "milter.local", "dmarc": {"result": "pass"}, "arc": {"result": "none"}},
]


def test_summarize_none_returns_empty() -> None:
    assert AuthenticationResults.summarize_authentication_results(None) == {}


def test_summarize_empty_list_returns_empty() -> None:
    assert AuthenticationResults.summarize_authentication_results([]) == {}


def test_summarize_accepts_a_single_dict() -> None:
    assert AuthenticationResults.summarize_authentication_results(COMBINED) == {
        "spf": "pass",
        "dkim": "pass",
        "dmarc": "pass",
    }


def test_summarize_merges_split_headers() -> None:
    assert AuthenticationResults.summarize_authentication_results(SPLIT) == {
        "spf": "pass",
        "dkim": "fail",
        "dmarc": "pass",
        "arc": "none",
    }


def test_summarize_first_verdict_wins() -> None:
    parsed = [
        {"server": "boundary", "spf": {"result": "pass"}},
        {"server": "upstream", "spf": {"result": "fail"}},
    ]
    assert AuthenticationResults.summarize_authentication_results(parsed) == {
        "spf": "pass",
    }


def test_summarize_ignores_mechanism_without_result() -> None:
    parsed = [
        {"server": "a", "spf": {}},
        {"server": "b", "dkim": {"result": "pass"}},
    ]
    assert AuthenticationResults.summarize_authentication_results(parsed) == {
        "dkim": "pass",
    }


def test_group_none_returns_empty() -> None:
    assert AuthenticationResults.group_authentication_results_by_server(None) == {}


def test_group_buckets_verdicts_by_authserv_id() -> None:
    assert AuthenticationResults.group_authentication_results_by_server(SPLIT) == {
        "mx.google.com": {"spf": "pass", "dkim": "fail"},
        "milter.local": {"dmarc": "pass", "arc": "none"},
    }


def test_group_missing_server_is_bucketed_as_unknown() -> None:
    parsed = [{"spf": {"result": "pass"}}]
    assert AuthenticationResults.group_authentication_results_by_server(parsed) == {
        "unknown": {"spf": "pass"},
    }


def test_group_skips_entries_without_verdicts() -> None:
    parsed = [{"server": "a"}, {"server": "b", "spf": {"result": "pass"}}]
    assert AuthenticationResults.group_authentication_results_by_server(parsed) == {
        "b": {"spf": "pass"},
    }


def test_collect_flattens_list_valued_header() -> None:
    headers = {
        "authentication-results": ["a; spf=pass", "b; dkim=pass"],
        "received": ["relay"],
    }
    assert AuthenticationResults.collect_authentication_results(headers) == [
        "a; spf=pass",
        "b; dkim=pass",
    ]


def test_collect_gathers_suffixed_keys() -> None:
    headers = {
        "Authentication-Results": "a; spf=pass",
        "Authentication-Results_1": "b; dkim=pass",
    }
    assert AuthenticationResults.collect_authentication_results(headers) == [
        "a; spf=pass",
        "b; dkim=pass",
    ]


def test_collect_returns_empty_when_absent() -> None:
    assert (
        AuthenticationResults.collect_authentication_results({"received": ["x"]}) == []
    )
