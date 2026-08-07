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

"""Normalize parsed Authentication-Results into per-message verdicts.

``mailsuite.utils.parse_authentication_results`` returns one parsed entry per
Authentication-Results header. Receivers vary in how they emit those headers:
some stamp a single combined header (e.g. Google), while a Postfix host running
separate OpenDKIM / OpenDMARC / SPF milters (as Proton does) prepends one header
per check. These helpers collapse either shape into a provider-independent view.
"""

from __future__ import annotations

import re

AUTH_METHODS = ("spf", "dkim", "dmarc", "arc")


def collect_authentication_results(headers: dict) -> list:
    """Collect every Authentication-Results header value from a headers mapping.

    Repeated headers may arrive either as a list under the
    "authentication-results" key (eml_parser shape) or as separate "_N"-suffixed
    keys (message_from_string shape); both shapes are flattened into one list.

    Args:
        headers: The email headers as a mapping of name to value(s).

    Returns:
        The Authentication-Results header values as a single flat list.
    """
    values = []
    for key, value in headers.items():
        if re.sub(r"_\d+$", "", key).lower() == "authentication-results":
            if isinstance(value, list):
                values.extend(value)
            else:
                values.append(value)
    return values


def _as_entries(parsed: list[dict] | dict | None) -> list[dict]:
    """Coerce parse_authentication_results output into a list of dicts."""
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    return [entry for entry in parsed if isinstance(entry, dict)]


def _verdicts(entry: dict) -> dict[str, str]:
    """Return the {method: result} verdicts contributed by a single header."""
    verdicts = {}
    for method in AUTH_METHODS:
        mechanism = entry.get(method)
        if isinstance(mechanism, dict) and mechanism.get("result"):
            verdicts[method] = mechanism["result"]
    return verdicts


def summarize_authentication_results(
    parsed: list[dict] | dict | None,
) -> dict[str, str]:
    """Merge parsed Authentication-Results into a single {method: result} map.

    Headers are processed in order and the first verdict seen for a method wins.
    Authentication-Results headers are prepended by each hop, so the topmost
    (closest, most-trusted boundary) header takes precedence over anything an
    upstream relay may have stamped further down.
    """
    summary = {}
    for entry in _as_entries(parsed):
        for method, result in _verdicts(entry).items():
            summary.setdefault(method, result)
    return summary


def group_authentication_results_by_server(
    parsed: list[dict] | dict | None,
) -> dict[str, dict[str, str]]:
    """Group the verdicts by authserv-id (each header's ``server`` field).

    Only Authentication-Results added by a trusted server should be believed, so
    keeping the verdicts bucketed by the server that produced them lets a
    consumer tell its own boundary MTA apart from an upstream relay that may have
    injected a forged result.
    """
    by_server = {}
    for entry in _as_entries(parsed):
        verdicts = _verdicts(entry)
        if not verdicts:
            continue
        bucket = by_server.setdefault(entry.get("server") or "unknown", {})
        for method, result in verdicts.items():
            bucket.setdefault(method, result)
    return by_server
