from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from huntbase.actions import ask_scout

from .. import common
from ..conftest import MockEntity
from ..core.session import CASE_ID

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput

    from ..core.product import Huntbase


def deadline() -> dict:
    # set_metadata stores parameters in the dict it is given, so each test needs its own copy
    return {"async_total_duration_deadline": int((time.time() + 3600) * 1000)}


def past() -> dict:
    # set_metadata stores parameters in the dict it is given, so each test needs its own copy
    return {"async_total_duration_deadline": int((time.time() - 10) * 1000)}


QUESTION = "Have we seen 203.0.113.10 elsewhere?"
DONE = {
    "state": "succeeded",
    "answer": "Yes, on two hosts.",
    "summary": "Seen twice.",
    "references": [{"label": "Firewall rows", "url": "https://x/r"}],
    "url": "https://x/a",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "Hunt ID": "h1"},
    entities=[MockEntity("203.0.113.10", "ADDRESS")],
    input_context=deadline() | {"case_id": CASE_ID},
)
def test_ask_scout_first_run_in_progress(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_scout_job("job_1", {"state": "queued"})

    ask_scout.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.IN_PROGRESS
    assert json.loads(results.result_value) == {"job_id": "job_1"}
    sent = huntbase.scout_questions[0]
    assert sent["question"].startswith(QUESTION)
    assert "Entities in the Google SecOps case: ip 203.0.113.10" in sent["question"]
    assert sent["hunt_id"] == "h1"
    assert sent["initiative"] == "medium"
    assert sent["external_ref"] == {"source": "google_secops", "id": str(CASE_ID)}


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "additional_data": json.dumps({"job_id": "job_9"})},
    input_context=deadline(),
)
def test_ask_scout_poll_completes(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_scout_job("job_9", DONE)

    ask_scout.main()

    results = action_output.results
    assert results.execution_state == ExecutionState.COMPLETED
    assert results.result_value is True
    assert "Yes, on two hosts." in results.output_message
    assert results.json_output.json_result["answer"] == "Yes, on two hosts."
    assert results.json_output.json_result["question"] == QUESTION
    assert results.json_output.json_result["references"][0]["label"] == "Firewall rows"
    assert huntbase.scout_questions == []


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "Include Case Context": "false"},
    input_context=deadline(),
)
def test_ask_scout_answers_immediately(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_scout_job("job_1", DONE)

    ask_scout.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "external_ref" not in huntbase.scout_questions[0]
    assert huntbase.scout_questions[0]["question"] == QUESTION


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "additional_data": json.dumps({"job_id": "job_9"})},
    input_context=deadline(),
)
def test_ask_scout_failed_job(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_scout_job("job_9", {"state": "failed", "error": "model unavailable"})

    ask_scout.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "model unavailable" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "additional_data": json.dumps({"job_id": "job_9"})},
    input_context=past(),
)
def test_ask_scout_async_timeout(huntbase: Huntbase, action_output: MockActionOutput) -> None:
    huntbase.add_scout_job("job_9", {"state": "running"})

    ask_scout.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "timed out" in action_output.results.output_message


@set_metadata(integration_config=common.CONFIG, parameters={"Question": "   "}, input_context=deadline())
def test_ask_scout_empty_question(action_output: MockActionOutput) -> None:
    ask_scout.main()

    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Question": QUESTION, "Initiative": "high"},
    input_context=deadline(),
)
def test_ask_scout_bad_initiative(action_output: MockActionOutput) -> None:
    ask_scout.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "Initiative must be one of" in action_output.results.output_message
