from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions.add_asm_issue_note import (
    AddAsmIssueNote,
    ERROR_MESSAGE,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        "Alert ID": "successful",
        "Text": "Test text",
    },
)
def test_add_asm_note(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    set_is_first_run_to_true()
    action = AddAsmIssueNote("NAME")
    action.run()

    assert len(script_session.request_history) == 2
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/asm/notes/issue/successful"
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={
        "Alert ID": "failing",
        "Text": "Test text",
    },
)
def test_add_asm_note_response_failed(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    set_is_first_run_to_true()
    action = AddAsmIssueNote("NAME")
    action.run()

    assert len(script_session.request_history) == 2
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/asm/notes/issue/failing"
    )

    assert ERROR_MESSAGE in action_output.results.output_message
    assert not action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.FAILED
