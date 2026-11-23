from __future__ import annotations

from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import start_hunt

from .. import common
from ..conftest import MockEntity
from ..core.session import CASE_ID

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase


def _entities() -> list[MockEntity]:
    return [
        MockEntity("203.0.113.10", "ADDRESS"),
        MockEntity("WS-0142", "HOSTNAME"),
        MockEntity("ws-0142", "HOSTNAME"),
        MockEntity("CVE-2026-0001", "CVE"),
    ]


@set_metadata(
    integration_config=common.CONFIG,
    entities=_entities(),
    input_context={"case_id": CASE_ID},
    parameters={
        "Hypothesis": "The host beaconed out",
        "Session Mode": "Autonomous",
        "Severity": "High",
        "Additional Seed Values": "evil.example, 203.0.113.10",
        "Case Link": "https://secops.example/cases/4821",
    },
)
def test_start_hunt_success(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    start_hunt.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "Successfully started Huntbase hunt hunt-new-1 with 3 seed value(s)" in results.output_message

    body = huntbase.started_hunts[0]
    assert body["seed_values"] == [
        {"type": "ip", "value": "203.0.113.10"},
        {"type": "hostname", "value": "WS-0142"},
        {"type": "domain", "value": "evil.example"},
    ]
    assert body["session_mode"] == "autonomous"
    assert body["severity"] == "high"
    assert body["hypothesis"] == "The host beaconed out"
    assert body["external_ref"] == {
        "source": "google_secops",
        "id": str(CASE_ID),
        "url": "https://secops.example/cases/4821",
        "title": body["title"],
    }
    assert body["title"] == f"Google SecOps case {CASE_ID}: 203.0.113.10"
    assert body["reuse_open"] is True
    assert body["title"].startswith("Google SecOps")

    json_result = results.json_output.json_result
    assert json_result["hunt_id"] == "hunt-new-1"
    assert json_result["seed_resolution"]["unresolved"][0] == {"type": "ip", "value": "203.0.113.10"}
    assert json_result["url"] == "https://huntbase.example.com/hunts/hunt-new-1?org=o1&src=api"


@set_metadata(integration_config=common.CONFIG, entities=[], parameters={"Title": "Manual"})
def test_start_hunt_without_seeds(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    start_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "No seeds for the hunt" in action_output.results.output_message
    assert huntbase.started_hunts == []


@set_metadata(integration_config=common.CONFIG, entities=_entities(), parameters={"Session Mode": "yolo"})
def test_start_hunt_bad_mode(action_output: MockActionOutput) -> None:
    start_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "Session Mode must be one of" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, entities=_entities(), parameters={"Title": "T"})
def test_start_hunt_forbidden(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.fail("start_hunt", 403, body={"detail": "hunt_session edit required"})

    start_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "hunt_session edit required" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    entities=_entities(),
    input_context={"case_id": CASE_ID},
    parameters={"Title": "T", "Case Link": "https://secops.example/cases/4821"},
)
def test_start_hunt_reopens_open_hunt(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.open_hunt_for_case = "hunt-open-7"

    start_hunt.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert "Successfully reopened Huntbase hunt hunt-open-7" in results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    entities=[MockEntity(f"10.0.0.{i}", "ADDRESS") for i in range(25)],
    parameters={"Reuse Open Hunt": "false"},
)
def test_start_hunt_caps_seed_values(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    start_hunt.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert len(huntbase.started_hunts[0]["seed_values"]) == 20
    assert "reuse_open" not in huntbase.started_hunts[0]


@set_metadata(integration_config=common.CONFIG, entities=_entities(), parameters={"Case Link": "cases/4821"})
def test_start_hunt_bad_case_link(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    start_hunt.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "Case Link must be an absolute http(s) URL" in action_output.results.output_message
    assert huntbase.started_hunts == []


@set_metadata(
    integration_config=common.CONFIG,
    entities=_entities(),
    input_context={"case_id": CASE_ID},
    parameters={"Title": "T"},
)
def test_start_hunt_without_case_link_does_not_reuse(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.open_hunt_for_case = "hunt-open-7"

    start_hunt.main()

    assert "Successfully started Huntbase hunt hunt-new-1" in action_output.results.output_message
    assert "reuse_open" not in huntbase.started_hunts[0]
    assert huntbase.started_hunts[0]["external_ref"]["id"] == str(CASE_ID)
