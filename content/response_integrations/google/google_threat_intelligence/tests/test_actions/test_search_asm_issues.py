"""Black-box tests for the Search ASM Issues action.

The action shares `ApiManager.search_issues_by_page()` with the ASM Issues
connector; these tests pin the action's contract (pagination, limit, empty
result and failed-search handling) through the real action entry point.
"""

from __future__ import annotations

from google_threat_intelligence.core.constants import DEFAULT_PAGE_SIZE, INTEGRATION_DISPLAY_NAME
from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions.search_asm_issues import (
    SearchASMIssues,
)
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api.common_responses import (
    create_asm_issue,
)
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.request import MockRequest
from integration_testing.set_meta import set_metadata

INTEGRATION_CONFIG_NO_ASM = {
    "API Root": "https://www.virustotal.com",
    "API Key": "TEST",
    "ASM Project Name": "",
    "Verify SSL": True,
}
SEARCH_ISSUES_PATH = "/api/v3/asm/search/issues/"
LAST_SEEN = "2026-10-06T10:00:00Z"
ISSUES_COUNT = 150
LIMIT = 120
EXECUTION_DEADLINE_MS = 4_102_444_800_000
INPUT_CONTEXT = {"execution_deadline_unix_time_ms": EXECUTION_DEADLINE_MS}
NO_SELECTION = "Select One"
SUCCESS_MESSAGE = (
    "Successfully returned issues based on the provided criteria "
    f"in {INTEGRATION_DISPLAY_NAME}."
)
NO_ISSUES_MESSAGE = (
    "No issues were found based on the provided criteria "
    f"in {INTEGRATION_DISPLAY_NAME}."
)
PARAMETERS = {
    "Project Name": "",
    "Issue ID": "",
    "Entity ID": "",
    "Entity Name": "example.com",
    "Time Parameter": "",
    "Time Frame": "Last Hour",
    "Start Time": "",
    "End Time": "",
    "Lowest Severity To Return": NO_SELECTION,
    "Status": NO_SELECTION,
    "Tags": "",
    "Max Issues To Return": str(LIMIT),
}


def get_search_requests(session: GoogleThreatIntelligenceSession) -> list[MockRequest]:
    """Get the requests sent to the ASM issues search endpoint"""
    return [
        record.request
        for record in session.request_history
        if record.request.url.path.startswith(SEARCH_ISSUES_PATH)
    ]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_issues_paginates_up_to_the_limit(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    google_threat_intelligence_product.add_asm_issues(
        [
            create_asm_issue(f"issue-{i}", last_seen=LAST_SEEN)
            for i in range(ISSUES_COUNT)
        ]
    )

    SearchASMIssues("NAME").run()

    search_requests = get_search_requests(script_session)
    assert [request.params["page"] for request in search_requests] == [["0"], ["1"]]
    assert all(
        request.params["page_size"] == [str(DEFAULT_PAGE_SIZE)]
        for request in search_requests
    )
    assert "entity_name:example.com" in search_requests[0].url.path.replace("%3A", ":")

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert len(action_output.results.json_output.json_result) == LIMIT


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_issues_reports_when_nothing_is_found(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()

    SearchASMIssues("NAME").run()

    assert len(get_search_requests(script_session)) == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == NO_ISSUES_MESSAGE


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_issues_completes_when_the_search_fails(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    """A `success: false` search answer is logged and treated as an empty result
    (the behaviour the action had before the connector fix)."""
    set_is_first_run_to_true()
    google_threat_intelligence_product.set_asm_search_error("Search failed")

    SearchASMIssues("NAME").run()

    assert len(get_search_requests(script_session)) == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == NO_ISSUES_MESSAGE
