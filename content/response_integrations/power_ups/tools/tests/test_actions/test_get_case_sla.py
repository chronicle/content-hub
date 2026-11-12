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

import copy
import sys
from typing import TYPE_CHECKING

import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import GetCaseSla
from ..common import ALERT_1_CONTEXT

if TYPE_CHECKING:
    import pytest
    from integration_testing.platform.script_output import MockActionOutput
    from TIPCommon.types import SingleJson

    from ..core.product import Tools
    from ..core.session import ToolsSession

SLA_EXPIRATION_MS = 1793087776558
CRITICAL_SLA_EXPIRATION_MS = 1793015776558
DEFAULT_PARAMS: dict[str, str] = {"DateTime Format": "%Y-%m-%d %H:%M:%S"}
NO_SLA_PAYLOAD: SingleJson = {
    "slaExpirationTime": -1,
    "criticalExpirationTime": -1,
    "expirationStatus": "NoSla",
    "remainingTimeSinceLastPause": -1,
}


@set_metadata(integration_config={}, parameters=dict(DEFAULT_PARAMS), input_context=copy.deepcopy(ALERT_1_CONTEXT))
def test_get_case_sla_one_platform_expands_sla_and_returns_formatted_timestamps(
    monkeypatch: pytest.MonkeyPatch,
    tools: Tools,
    script_session: ToolsSession,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--onePlatformSupport"])
    tools.set_case_metadata({
        "id": 123,
        "displayName": "Sample Case",
        "priority": 60,
        "status": 1,
        "sla": {
            "expirationTime": SLA_EXPIRATION_MS,
            "criticalExpirationTime": CRITICAL_SLA_EXPIRATION_MS,
            "expirationStatus": "OpenSla",
            "remainingTimeSinceLastPause": -1,
        },
    })

    GetCaseSla.main()

    assert len(script_session.request_history) == 2
    case_request = script_session.request_history[0].request
    assert case_request.url.path.endswith("/cases/123")
    assert case_request.kwargs.get("params") == {"expand": "sla"}

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "SLA_unix": SLA_EXPIRATION_MS,
        "SLA": "2026-10-27 07:56:16",
        "critical_SLA_unix": CRITICAL_SLA_EXPIRATION_MS,
        "critical_SLA": "2026-10-26 11:56:16",
    }
    assert (
        action_output.results.output_message
        == "Stage SLA: 2026-10-27 07:56:16, Critical Stage SLA: 2026-10-26 11:56:16"
    )


@set_metadata(integration_config={}, parameters=dict(DEFAULT_PARAMS), input_context=copy.deepcopy(ALERT_1_CONTEXT))
def test_get_case_sla_active_sla_without_critical_sla_returns_none_for_critical_fields(
    monkeypatch: pytest.MonkeyPatch,
    tools: Tools,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--onePlatformSupport"])
    tools.set_case_metadata({
        "id": 123,
        "displayName": "Case Without Critical SLA",
        "priority": 60,
        "status": 1,
        "sla": {
            "expirationTime": SLA_EXPIRATION_MS,
            "criticalExpirationTime": -1,
            "expirationStatus": "OpenSla",
            "remainingTimeSinceLastPause": -1,
        },
    })

    GetCaseSla.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "SLA_unix": SLA_EXPIRATION_MS,
        "SLA": "2026-10-27 07:56:16",
        "critical_SLA_unix": None,
        "critical_SLA": None,
    }
    assert action_output.results.output_message == "Stage SLA: 2026-10-27 07:56:16, Critical Stage SLA: None"


@set_metadata(
    integration_config={},
    parameters={"DateTime Format": "%Y/%m/%d %H:%M"},
    input_context=copy.deepcopy(ALERT_1_CONTEXT),
)
def test_get_case_sla_legacy_falls_back_to_stage_sla_when_case_sla_is_negative_one(
    monkeypatch: pytest.MonkeyPatch,
    tools: Tools,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", [arg for arg in sys.argv if arg != "--onePlatformSupport"])
    tools.set_case_metadata({
        "id": 123,
        "name": "Legacy Stage SLA Case",
        "priority": 60,
        "status": 1,
        "sla": copy.deepcopy(NO_SLA_PAYLOAD),
        "stageSla": {
            "slaExpirationTime": SLA_EXPIRATION_MS,
            "criticalExpirationTime": CRITICAL_SLA_EXPIRATION_MS,
            "expirationStatus": "OpenSla",
            "remainingTimeSinceLastPause": -1,
        },
    })

    GetCaseSla.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "SLA_unix": SLA_EXPIRATION_MS,
        "SLA": "2026/10/27 07:56",
        "critical_SLA_unix": CRITICAL_SLA_EXPIRATION_MS,
        "critical_SLA": "2026/10/26 11:56",
    }


@set_metadata(integration_config={}, parameters=dict(DEFAULT_PARAMS), input_context=copy.deepcopy(ALERT_1_CONTEXT))
def test_get_case_sla_no_sla_configured_completes_with_false_result(
    monkeypatch: pytest.MonkeyPatch,
    tools: Tools,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--onePlatformSupport"])
    tools.set_case_metadata({
        "id": 123,
        "displayName": "Case Without SLA",
        "priority": 40,
        "status": 1,
        "sla": copy.deepcopy(NO_SLA_PAYLOAD),
    })

    GetCaseSla.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is False
    assert action_output.results.json_output is None
    assert action_output.results.output_message == "SLA was not set for case 123."


@set_metadata(integration_config={}, parameters=dict(DEFAULT_PARAMS), input_context=copy.deepcopy(ALERT_1_CONTEXT))
def test_get_case_sla_api_error_fails_with_standard_error_message(
    monkeypatch: pytest.MonkeyPatch,
    tools: Tools,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--onePlatformSupport"])
    tools.case_details_error = requests.HTTPError("500 Server Error")

    GetCaseSla.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert 'Error executing action "Get Case SLA". Reason: 500 Server Error' in action_output.results.output_message
