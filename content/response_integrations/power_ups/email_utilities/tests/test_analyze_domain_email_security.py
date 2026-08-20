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


def test_strong_spf_true_only_for_hard_fail() -> None:
    spf = {"record": "v=spf1 -all", "parsed": {"all": "fail"}}
    assert build_result("x.example", _domain_check(spf))["StrongSPF"] is True
    # A softfail policy is not strong: receivers commonly deliver softfailing
    # mail, so counting "~all" (as the pre-53.0 field did) overstates it.
    for all_value in ("softfail", "neutral"):
        spf = {"record": "v=spf1 ...", "parsed": {"all": all_value}}
        assert build_result("x.example", _domain_check(spf))["StrongSPF"] is False


def test_strong_spf_falls_back_to_record_suffix() -> None:
    assert (
        build_result("x.example", _domain_check({"record": "v=spf1 a -all"}))[
            "StrongSPF"
        ]
        is True
    )
    for record in ("v=spf1 a ~all", "v=spf1 a ?all"):
        assert (
            build_result("x.example", _domain_check({"record": record}))["StrongSPF"]
            is False
        )


def test_strong_spf_false_when_spf_missing() -> None:
    result = build_result("x.example", _domain_check(None))
    assert result["SPF"] is None
    assert result["StrongSPF"] is False
