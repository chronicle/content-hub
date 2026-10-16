from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from TIPCommon.base.action import ExecutionState

from houdin_io.actions import scan_artifact
from houdin_io.tests.conftest import run_action
from houdin_io.tests.mock_session import HoudinSession

ARTIFACT = {"Artifact": "5.149.250.54"}


def first_run(action_output: MockActionOutput, parameters: dict | None = None) -> str:
    """Launch, assert IN_PROGRESS, return the state handed back for the next run."""
    run_action(scan_artifact.main, parameters or ARTIFACT)
    results = action_output.results
    assert results.execution_state == ExecutionState.IN_PROGRESS
    action_output.flush()
    return results.result_value


class TestScanArtifact:
    def test_first_run_launches_and_waits(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        run_action(scan_artifact.main, ARTIFACT)

        results = action_output.results
        assert results.execution_state == ExecutionState.IN_PROGRESS
        state = json.loads(results.result_value)
        assert state["scanID"] in houdin.launched
        assert "in progress" in results.output_message
        launch = houdin.request_history[0].request
        assert launch.url.path == "/api/v1/scan/launch"
        assert launch.kwargs["json"] == {"artifact": "5.149.250.54"}
        assert launch.headers["X-API-Key"] == "test-api-key"

    def test_explicit_scanners_get_mesmer_and_force_rescan(
        self, houdin: HoudinSession, action_output: MockActionOutput
    ) -> None:
        run_action(scan_artifact.main, {**ARTIFACT, "Scanners": "vt, abuseipdb", "Force Rescan": "true"})

        payload = houdin.request_history[0].request.kwargs["json"]
        assert payload["scanners"] == ["vt", "abuseipdb", "mesmer", "mesmer-summary"]
        assert payload["forceRescan"] is True

    def test_scan_finishing_within_the_run_completes_on_first_run(
        self, houdin: HoudinSession, action_output: MockActionOutput
    ) -> None:
        houdin.finish_after_reads = 2

        run_action(scan_artifact.main, ARTIFACT)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert houdin.reads == 3, "polled until the scan was done, then stopped"

    def test_cache_hit_completes_on_first_run(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.launch_status = "Done"

        run_action(scan_artifact.main, ARTIFACT)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert results.json_output.json_result["artifact"] == "5.149.250.54"
        assert "8/10, high confidence" in results.output_message

    def test_second_run_still_waiting(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        state = first_run(action_output)

        run_action(scan_artifact.main, {**ARTIFACT, "additional_data": state})

        results = action_output.results
        assert results.execution_state == ExecutionState.IN_PROGRESS
        assert results.result_value == state
        assert len(houdin.launched) == 1, "a continuation run must not launch again"

    def test_second_run_returns_document(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        state = first_run(action_output)
        houdin.finish()

        run_action(scan_artifact.main, {**ARTIFACT, "additional_data": state})

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        document = results.json_output.json_result
        assert document["scanID"] == json.loads(state)["scanID"]
        assert document["scanResults"]["mesmer"]["result"]["globalScore"] == 8
        assert "app.houdin.io/scans/" in results.output_message

    def test_refusal_fails_with_houdin_message(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.refuse["10.0.0.1"] = (400, "No compatible scanners found for this artifact")

        run_action(scan_artifact.main, {"Artifact": "10.0.0.1"})

        results = action_output.results
        assert results.execution_state == ExecutionState.FAILED
        assert "No compatible scanners found for this artifact" in results.output_message

    def test_rejected_key_fails(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.key_valid = False

        run_action(scan_artifact.main, ARTIFACT)

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Invalid API Key" in action_output.results.output_message
