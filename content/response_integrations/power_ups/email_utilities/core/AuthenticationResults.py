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
an integrated engine that runs every check in one pass (Gmail, Microsoft 365,
Rspamd, Amavis) stamps a single combined header, while a receiver composed of
separate filters must stamp one header per check — RFC 8601 section 4 lets an
MTA add the field "either once per test or once indicating all of the results"
and forbids adding a result to an existing header field. The split shape is
therefore typical of Postfix or Sendmail hosts running separate OpenDKIM /
OpenDMARC / SPF milters; Proton Mail is a real-world example (its inbound
Postfix hosts stamp separate ``mail.protonmail.ch`` headers for dkim, dmarc,
spf, and arc). It is a property of the filter architecture, not of Postfix
itself. These helpers collapse either shape into a provider-independent view.

A message may also carry an ``Authentication-Results-Original`` header when a
Secure Email Gateway (e.g. Proofpoint, Cisco Secure Email) preserves the
results recorded at the internet boundary before re-stamping its own; callers
can collect that header instead via ``header_name``. Like Authentication-Results
itself it is trivial to forge, so it should only be trusted when the receiving
organization's own gateway is known to write it.
"""

from __future__ import annotations

import re

AUTH_METHODS = ("spf", "dkim", "dmarc", "arc")


def collect_authentication_results(
    headers: dict,
    header_name: str = "authentication-results",
) -> list:
    """Collect every value of an authentication header from a headers mapping.

    Repeated headers may arrive either as a list under a single key (eml_parser
    shape) or as separate "_N"-suffixed keys (message_from_string shape); both
    shapes are flattened into one list, preserving message order (topmost
    header first).

    Args:
        headers: The email headers as a mapping of name to value(s).
        header_name: The header to collect, e.g. "authentication-results"
            (default) or "authentication-results-original".

    Returns:
        The header values as a single flat list.
    """
    values = []
    for key, value in headers.items():
        if re.sub(r"_\d+$", "", key).lower() == header_name:
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
    allow_multiple: bool = False,
) -> dict[str, str]:
    """Merge parsed Authentication-Results into a single {method: result} map.

    Authentication-Results headers are prepended by each hop, so the topmost
    header is the one stamped by the receiving server and is the only one that
    should be believed by default: anything further down may have been forged
    by the sender before the message was received. By default only that topmost
    header contributes to the summary.

    Set ``allow_multiple`` to True only when the receiving mail service splits
    the checks across separate headers (e.g. Proton Mail; see the module
    docstring). Headers are then processed in order and the first verdict seen
    for a method wins, so a topmost verdict still shadows anything an upstream
    relay (or a sender) stamped further down for the same method.

    Args:
        parsed: Output of ``mailsuite.utils.parse_authentication_results``.
        allow_multiple: Merge verdicts across every header instead of using
            only the topmost one.

    Returns:
        A {method: result} map, e.g. {"spf": "pass", "dkim": "fail"}.
    """
    entries = _as_entries(parsed)
    if not allow_multiple:
        entries = entries[:1]
    summary = {}
    for entry in entries:
        for method, result in _verdicts(entry).items():
            summary.setdefault(method, result)
    return summary


def get_dmarc_from_domain(parsed: list[dict] | dict | None) -> str | None:
    """Return the RFC 5322 From domain that DMARC evaluated.

    The receiver records it as the dmarc method's ``header.from`` property
    (RFC 8601). The dkim method's ``header.i`` property is a different
    identity (the AUID) and only coincides with the DMARC domain when DKIM
    happens to be aligned, so it must not be used for this. Entries are
    scanned topmost-first and the first DMARC verdict wins.
    """
    for entry in _as_entries(parsed):
        dmarc = entry.get("dmarc")
        if isinstance(dmarc, dict) and dmarc.get("header.from"):
            return str(dmarc["header.from"])
    return None


def get_spf_mail_from_domain(parsed: list[dict] | dict | None) -> str | None:
    """Return the domain of the RFC 5321 MAIL FROM that SPF evaluated.

    The receiver records it as the spf method's ``smtp.mailfrom`` property
    (RFC 8601), which may be a full address or a bare domain. Entries are
    scanned topmost-first and the first SPF verdict wins.
    """
    for entry in _as_entries(parsed):
        spf = entry.get("spf")
        if isinstance(spf, dict) and spf.get("smtp.mailfrom"):
            mailfrom = str(spf["smtp.mailfrom"])
            return mailfrom.rpartition("@")[2] or mailfrom
    return None


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
