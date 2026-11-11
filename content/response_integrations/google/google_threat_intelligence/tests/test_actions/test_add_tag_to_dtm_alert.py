from __future__ import annotations


from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions.add_tag_to_dtm_alert import (
    AddTagToDtmAlert,
    ERROR_MESSAGE,
)

from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.request import HttpMethod
from integration_testing.set_meta import set_metadata

INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={"Alert ID": "successful", "Tags": "Tag1,Tag2", "Mode": "Set"},
)
def test_add_tag_to_dtm_alert_with_set_mode(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    set_is_first_run_to_true()
    action = AddTagToDtmAlert("NAME")
    action.run()

    assert len(script_session.request_history) == 2
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert script_session.request_history[1].request.method == HttpMethod.PATCH
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/dtm/alerts/successful"
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={"Alert ID": "successful", "Tags": "Tag1,Tag2", "Mode": "Append"},
)
def test_add_tag_to_dtm_alert_with_append_mode(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    set_is_first_run_to_true()
    action = AddTagToDtmAlert("NAME")
    action.run()

    assert len(script_session.request_history) == 3
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert script_session.request_history[1].request.method == HttpMethod.GET
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/dtm/alerts/successful"
    )
    assert script_session.request_history[2].request.method == HttpMethod.PATCH
    assert (
        script_session.request_history[2].request.url.path
        == "/api/v3/dtm/alerts/successful"
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters={"Alert ID": "failed", "Tags": "Tag1,Tag2", "Mode": "Append"},
)
def test_add_tag_to_dtm_alert_with_append_mode_failed_to_add(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    set_is_first_run_to_true()
    action = AddTagToDtmAlert("NAME")
    action.run()

    assert len(script_session.request_history) == 3
    assert (
        script_session.request_history[0].request.url.path
        == "/api/v3/metadata"
    )
    assert script_session.request_history[1].request.method == HttpMethod.GET
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/dtm/alerts/failed"
    )
    assert script_session.request_history[2].request.method == HttpMethod.PATCH
    assert (
        script_session.request_history[2].request.url.path
        == "/api/v3/dtm/alerts/failed"
    )

    assert ERROR_MESSAGE in action_output.results.output_message
    assert not action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.FAILED
