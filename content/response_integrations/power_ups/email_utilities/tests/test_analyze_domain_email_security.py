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

from typing import Any

import pytest
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)

from ..actions import AnalyzeDomainEmailSecurity
from ..actions.AnalyzeDomainEmailSecurity import build_result, main


class _FakeLogger:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)


class _FakeResult:
    def __init__(self) -> None:
        self.json_results: list[dict] = []

    def add_result_json(self, result: dict) -> None:
        self.json_results.append(result)


class _FakeSiemplifyAction:
    """Minimal SiemplifyAction stand-in that records the end() call."""

    def __init__(self, params: dict) -> None:
        self._params = params
        self.script_name: str | None = None
        self.result = _FakeResult()
        self.LOGGER = _FakeLogger()
        self.end_message: str | None = None
        self.end_result_value: str | None = None
        self.end_status: int | None = None

    def extract_action_param(
        self,
        param_name: str,
        print_value: bool = False,
        input_type: type = str,
        default_value: Any = None,
    ) -> Any:
        return self._params.get(param_name, default_value)

    def end(self, message: str, result_value: str, status: int) -> None:
        self.end_message = message
        self.end_result_value = result_value
        self.end_status = status


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    params: dict,
    domain_check: dict | None = None,
) -> _FakeSiemplifyAction:
    """Run the action's main() with a stubbed platform and checkdmarc."""
    siemplify = _FakeSiemplifyAction(params)
    monkeypatch.setattr(
        AnalyzeDomainEmailSecurity,
        "SiemplifyAction",
        lambda: siemplify,
    )

    def fake_check_domains(domains: list[str], **kwargs: Any) -> dict:
        assert domain_check is not None, "checkdmarc must not be called"
        return domain_check

    monkeypatch.setattr(
        AnalyzeDomainEmailSecurity.checkdmarc,
        "check_domains",
        fake_check_domains,
    )
    main()
    return siemplify


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


@pytest.mark.parametrize("domain", [None, "", "   ", "\t\n"])
def test_main_fails_on_empty_domain(
    monkeypatch: pytest.MonkeyPatch,
    domain: str | None,
) -> None:
    # An empty or whitespace-only Domain must raise ValueError inside main(),
    # which surfaces as EXECUTION_STATE_FAILED without ever calling checkdmarc.
    siemplify = _run_main(monkeypatch, {"Domain": domain}, domain_check=None)
    assert siemplify.end_status == EXECUTION_STATE_FAILED
    assert siemplify.end_result_value == "false"
    assert 'the "Domain" parameter must not be empty' in siemplify.end_message
    assert siemplify.LOGGER.errors
    assert siemplify.result.json_results == []


def test_main_result_value_false_when_spf_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = _domain_check({"record": "v=spf1 +all", "valid": False})
    siemplify = _run_main(monkeypatch, {"Domain": "x.example"}, check)
    assert siemplify.end_status == EXECUTION_STATE_COMPLETED
    assert siemplify.end_result_value == "false"


def test_main_result_value_false_when_dmarc_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = _domain_check({"record": "v=spf1 -all", "valid": True})
    check["dmarc"] = None
    siemplify = _run_main(monkeypatch, {"Domain": "x.example"}, check)
    assert siemplify.end_status == EXECUTION_STATE_COMPLETED
    assert siemplify.end_result_value == "false"


def test_main_result_value_true_when_spf_and_dmarc_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    check = _domain_check({"record": "v=spf1 -all", "valid": True})
    siemplify = _run_main(monkeypatch, {"Domain": "X.Example"}, check)
    assert siemplify.end_status == EXECUTION_STATE_COMPLETED
    assert siemplify.end_result_value == "true"
    # The Domain parameter is normalized before use.
    assert siemplify.result.json_results[0]["Domain"] == "x.example"
