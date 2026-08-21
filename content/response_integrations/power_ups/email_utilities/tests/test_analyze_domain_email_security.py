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

"""Unit tests for the Analyze Domain Email Security result assembly."""

from __future__ import annotations

from ..actions.AnalyzeDomainEmailSecurity import build_result


def _domain_check(spf: dict | None) -> dict:
    return {
        "domain": "x.example",
        "dnssec": True,
        "mx": {"hosts": [], "warnings": []},
        "spf": spf,
        "dmarc": {"record": "v=DMARC1; p=reject", "valid": True},
        "mta_sts": {"valid": True, "id": "20240101", "policy": {"mode": "enforce"}},
        "smtp_tls_reporting": {"valid": True, "rua": ["mailto:tls@x.example"]},
        "bimi": {"valid": True, "selector": "default", "record": "v=BIMI1;"},
    }


def test_build_result_passes_checkdmarc_structures_through_verbatim() -> None:
    spf = {"record": "v=spf1 -all", "valid": True, "parsed": {"all": "fail"}}
    check = _domain_check(spf)
    result = build_result("x.example", check)
    assert result["Domain"] == "x.example"
    assert result["SPF"] is check["spf"]
    assert result["DMARC"] is check["dmarc"]
    assert result["MX"] is check["mx"]
    assert result["DNSSec"] is True
    assert result["MTASTS"] is check["mta_sts"]
    assert result["SMTPTLSReporting"] is check["smtp_tls_reporting"]
    assert result["BIMI"] is check["bimi"]


def test_build_result_does_not_reproduce_strong_spf() -> None:
    # The pre-53.0 StrongSPF boolean is deliberately absent; the policy it
    # summarized is available verbatim as SPF["parsed"]["all"].
    spf = {"record": "v=spf1 -all", "parsed": {"all": "fail"}}
    result = build_result("x.example", _domain_check(spf))
    assert "StrongSPF" not in result
    assert result["SPF"]["parsed"]["all"] == "fail"


def test_build_result_tolerates_missing_spf() -> None:
    result = build_result("x.example", _domain_check(None))
    assert result["SPF"] is None
