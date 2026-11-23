from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import get_hunt

from .. import common

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase


def far_deadline() -> dict:
    # set_metadata stores parameters in the dict it is given, so each test needs its own copy
    return {"async_total_duration_deadline": int((time.time() + 3600) * 1000)}


def past_deadline() -> dict:
    # set_metadata stores parameters in the dict it is given, so each test needs its own copy
    return {"async_total_duration_deadline": int((time.time() - 10) * 1000)}


FINDING = {
    "id": "f1",
    "session_id": "h1",
    "title": "Beaconing",
    "disposition": "confirmed",
    "severity": "high",
    "entities": [{"type": "host", "value": "WS-0142", "role": "source"}],
    "created_at": "2026-11-21T14:40:00Z",
}


@set_metadata(integration_config=common.CONFIG, parameters={"Hunt ID": "h1"}, input_context=far_deadline())
def test_get_hunt_concluded(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_hunt(
        "h1",
        status="concluded",
        latest_verdict={"disposition": "confirmed", "reason": "Beacon confirmed.", "author_type": "user"},
    )
    huntbase.hunt_findings["h1"] = [FINDING]

    get_hunt.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "status: concluded, verdict: confirmed" in results.output_message
    assert "Findings: 1." in results.output_message
    data = results.json_output.json_result
    assert data["verdict"] == "confirmed"
    assert data["summary"] == "Beacon confirmed."
    assert data["url"] == f"{common.APP_ROOT}/hunts/h1?src=google_secops"
    assert data["findings"][0]["url"] == f"{common.APP_ROOT}/findings/f1?src=google_secops"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Hunt ID": "h1", "Include Findings": "false"},
    input_context=far_deadline(),
)
def test_get_hunt_running_without_wait(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_hunt("h1", status="active")

    get_hunt.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert "findings" not in results.json_output.json_result


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Hunt ID": "h1", "Wait For Completion": "true"},
    input_context=far_deadline(),
)
def test_get_hunt_wait_in_progress(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_hunt("h1", status="active")

    get_hunt.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.IN_PROGRESS
    assert json.loads(results.result_value) == {"hunt_id": "h1", "status": "active"}
    assert "Waiting for Huntbase hunt h1" in results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Hunt ID": "h1", "Wait For Completion": "true"},
    input_context=past_deadline(),
)
def test_get_hunt_wait_timeout(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_hunt("h1", status="active")

    get_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "still active when the action timed out" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters={"Hunt ID": "missing"}, input_context=far_deadline())
def test_get_hunt_not_found(action_output: MockActionOutput) -> None:
    get_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "Session not found" in action_output.results.output_message
