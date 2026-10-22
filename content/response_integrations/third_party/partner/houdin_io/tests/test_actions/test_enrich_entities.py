from __future__ import annotations

import json
from typing import TYPE_CHECKING

from integration_testing.platform.script_output import MockActionOutput
from TIPCommon.base.action import ExecutionState

from houdin_io.actions import enrich_entities
from houdin_io.tests.conftest import make_entity, run_action
from houdin_io.tests.mock_session import HoudinSession

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

IP = make_entity("5.149.250.54", "ADDRESS")
PRIVATE_IP = make_entity("10.0.0.7", "ADDRESS")
URL = make_entity("HTTP://MARKOSSOLOMON.COM/F1Q7QX.PHP", "DestinationURL")
DOMAIN = make_entity("update-service.win", "DOMAIN")
HOSTNAME = make_entity("WS-0042", "HOSTNAME")
USER = make_entity("jdoe", "USERUNIQNAME")
ENTITIES: list[DomainEntityInfo] = [IP, PRIVATE_IP, URL, DOMAIN, HOSTNAME, USER]
SCANNED: set[str] = {IP.identifier, URL.identifier, DOMAIN.identifier}


def reset_entities() -> None:
    for entity in ENTITIES:
        entity.additional_properties = {}
        entity.is_suspicious = False
        entity.is_enriched = False


def first_run(
    action_output: MockActionOutput,
    parameters: SingleJson | None = None,
    entities: list[DomainEntityInfo] = ENTITIES,
) -> str:
    """Launch, assert IN_PROGRESS, return the state handed back for the next run."""
    run_action(enrich_entities.main, parameters, entities)
    results = action_output.results
    assert results.execution_state == ExecutionState.IN_PROGRESS
    action_output.flush()
    return results.result_value


def run_until_done(
    houdin: HoudinSession,
    action_output: MockActionOutput,
    parameters: SingleJson | None = None,
) -> None:
    """First run launches, finish() every scan, second run completes."""
    parameters = dict(parameters or {})
    parameters["additional_data"] = first_run(action_output, parameters)
    houdin.finish()
    run_action(enrich_entities.main, parameters, ENTITIES)


class TestEnrichEntities:
    def setup_method(self) -> None:
        reset_entities()

    def test_only_scannable_entities_are_launched(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        run_action(enrich_entities.main, {}, ENTITIES)

        results = action_output.results
        assert results.execution_state == ExecutionState.IN_PROGRESS
        assert set(houdin.launched.values()) == SCANNED
        state: SingleJson = json.loads(results.result_value)
        assert set(state["scans"].values()) == SCANNED
        assert state["done"] == [] and state["failed"] == {}
        assert len(houdin.result_reads()) == 1, "one poll per run, then back to the platform"

    def test_cached_scans_complete_on_first_run(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.launch_status = "Done"

        run_action(enrich_entities.main, {}, ENTITIES)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert results.result_value is True
        assert IP.additional_properties["Houdin-io_Threat_Score"] == "8"
        assert len(houdin.result_reads()) == 1, "the documents of this run are not read a second time"

    def test_enrichment_and_json_result(
        self,
        houdin: HoudinSession,
        action_output: MockActionOutput,
        update_entities: MagicMock,
        add_entity_insight: MagicMock,
    ) -> None:
        houdin.scores[DOMAIN.identifier] = 3

        run_until_done(houdin, action_output)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert results.result_value is True
        assert IP.additional_properties["Houdin-io_Threat_Score"] == "8"
        assert IP.additional_properties["Houdin-io_Confidence"] == "high"
        assert IP.additional_properties["Houdin-io_Tags"].startswith("Malicious hosting infrastructure")
        assert IP.additional_properties["Houdin-io_Sources"] == (
            "urlscan, vt, abuseipdb, alienvault, triage, threatfox, urlhaus, netlas"
        )
        assert IP.additional_properties["Houdin-io_Scan_Link"].startswith("https://app.houdin.io/scans/")
        assert "Houdin-io_Unrecorded" not in IP.additional_properties
        assert IP.is_suspicious is True and IP.is_enriched is True
        assert DOMAIN.additional_properties["Houdin-io_Threat_Score"] == "3"
        assert DOMAIN.is_suspicious is False
        assert PRIVATE_IP.additional_properties == {} and USER.additional_properties == {}
        json_result: list[SingleJson] = results.json_output.json_result
        assert {row["Entity"] for row in json_result} == SCANNED
        assert all(row["EntityResult"]["scanResults"]["mesmer"]["result"]["globalScore"] for row in json_result)
        assert update_entities.call_count == 1
        assert add_entity_insight.call_count == 3
        assert "Enriched 3 entities" in results.output_message

    def test_partial_completion_enriches_as_scans_finish(
        self,
        houdin: HoudinSession,
        action_output: MockActionOutput,
    ) -> None:
        state: str = first_run(action_output)
        houdin.finish(IP.identifier)
        houdin.clear_record()

        run_action(enrich_entities.main, {"additional_data": state}, ENTITIES)

        results = action_output.results
        assert results.execution_state == ExecutionState.IN_PROGRESS
        assert "still scanning 2 entities" in results.output_message
        assert IP.additional_properties["Houdin-io_Threat_Score"] == "8"
        assert DOMAIN.additional_properties == {}
        new_state: SingleJson = json.loads(results.result_value)
        assert len(new_state["done"]) == 1
        assert len(houdin.launched) == 3, "continuation runs never relaunch"
        reads: list[list[str]] = houdin.result_reads()
        assert len(reads) == 1 and len(reads[0]) == 3, "one bulk read of the pending scans"
        assert not [r for r in houdin.request_history if r.request.url.path == "/api/v1/scan/launch"]

    def test_final_run_reads_again_only_the_scans_done_earlier(
        self,
        houdin: HoudinSession,
        action_output: MockActionOutput,
    ) -> None:
        state: str = first_run(action_output)
        houdin.finish(IP.identifier)
        run_action(enrich_entities.main, {"additional_data": state}, ENTITIES)
        state = action_output.results.result_value
        action_output.flush()
        houdin.finish()
        houdin.clear_record()

        run_action(enrich_entities.main, {"additional_data": state}, ENTITIES)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        reads: list[list[str]] = houdin.result_reads()
        assert [len(ids) for ids in reads] == [2, 1], "the pending pair, then the one scan enriched by the earlier run"
        assert {row["Entity"] for row in results.json_output.json_result} == SCANNED

    def test_threshold_and_insight_parameters(
        self,
        houdin: HoudinSession,
        action_output: MockActionOutput,
        add_entity_insight: MagicMock,
    ) -> None:
        run_until_done(houdin, action_output, {"Suspicious Threshold": "9", "Create Insight": "false"})

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert IP.is_suspicious is False
        assert add_entity_insight.call_count == 0

    def test_threshold_off(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.scores[IP.identifier] = 10

        run_until_done(houdin, action_output, {"Suspicious Threshold": "off"})

        assert IP.is_suspicious is False

    def test_invalid_threshold_fails(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        run_action(enrich_entities.main, {"Suspicious Threshold": "high"}, ENTITIES)

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Suspicious Threshold" in action_output.results.output_message
        assert houdin.launched == {}

    def test_refused_artifact_is_reported_and_others_continue(
        self,
        houdin: HoudinSession,
        action_output: MockActionOutput,
    ) -> None:
        houdin.refuse[URL.identifier] = (403, "Scanners not available on your plan: misp")

        run_until_done(houdin, action_output)

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert results.result_value is True
        assert "Enriched 2 entities" in results.output_message
        assert "not scanned, Scanners not available on your plan: misp" in results.output_message
        assert URL.additional_properties == {}

    def test_account_error_fails_the_action(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.key_valid = False

        run_action(enrich_entities.main, {}, ENTITIES)

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Invalid API Key" in action_output.results.output_message

    def test_scan_without_verdict(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.scores[IP.identifier] = None

        run_until_done(houdin, action_output)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Houdin-io_Threat_Score" not in IP.additional_properties
        assert IP.additional_properties["Houdin-io_Scan_Link"]
        assert IP.is_suspicious is False

    def test_no_scannable_entity(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        run_action(enrich_entities.main, {}, [PRIVATE_IP, USER])

        results = action_output.results
        assert results.execution_state == ExecutionState.COMPLETED
        assert results.result_value is False
        assert "No entity was scanned" in results.output_message
        assert houdin.request_history == []
