"""Black-box tests for the Search ASM Entities action.

The action shares `ApiManager.search_issues_by_page()` with the ASM Issues
connector; these tests pin the action's contract (pagination, limit, empty
result and failed-search handling) through the real action entry point.
"""

from __future__ import annotations

from google_threat_intelligence.core.constants import DEFAULT_PAGE_SIZE, INTEGRATION_DISPLAY_NAME
from TIPCommon.base.action import ExecutionState

from google_threat_intelligence.actions.search_asm_entities import (
    SearchASMEntities,
)
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api.common_responses import (
    create_asm_entity,
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
SEARCH_ENTITIES_PATH = "/api/v3/asm/search/entities/"
ENTITIES_COUNT = 150
LIMIT = 120
EXECUTION_DEADLINE_MS = 4_102_444_800_000
INPUT_CONTEXT = {"execution_deadline_unix_time_ms": EXECUTION_DEADLINE_MS}
SUCCESS_MESSAGE = (
    "Successfully returned entities based on the provided criteria "
    f"in {INTEGRATION_DISPLAY_NAME}."
)
NO_ENTITIES_MESSAGE = (
    "No entities were found based on the provided "
    f"criteriain {INTEGRATION_DISPLAY_NAME}."
)
PARAMETERS = {
    "Project Name": "",
    "Entity Name": "example.com",
    "Minimum Vulnerabilities Count": "",
    "Minimum Issues Count": "",
    "Tags": "",
    "Max Entities To Return": str(LIMIT),
    "Critical or High Issue": "false",
}


def get_search_requests(session: GoogleThreatIntelligenceSession) -> list[MockRequest]:
    """Get the requests sent to the ASM entities search endpoint"""
    return [
        record.request
        for record in session.request_history
        if record.request.url.path.startswith(SEARCH_ENTITIES_PATH)
    ]


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_entities_paginates_up_to_the_limit(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()
    google_threat_intelligence_product.add_asm_entities(
        [create_asm_entity(f"host-{i}.example.com") for i in range(ENTITIES_COUNT)]
    )

    SearchASMEntities("NAME").run()

    search_requests = get_search_requests(script_session)
    assert [request.params["page"] for request in search_requests] == [["0"], ["1"]]
    assert all(
        request.params["page_size"] == [str(DEFAULT_PAGE_SIZE)]
        for request in search_requests
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert len(action_output.results.json_output.json_result) == LIMIT


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_entities_reports_when_nothing_is_found(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:
    set_is_first_run_to_true()

    SearchASMEntities("NAME").run()

    assert len(get_search_requests(script_session)) == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == NO_ENTITIES_MESSAGE


@set_metadata(
    integration_config=INTEGRATION_CONFIG_NO_ASM,
    parameters=PARAMETERS,
    input_context=INPUT_CONTEXT,
)
def test_search_asm_entities_completes_when_the_search_fails(
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    action_output: MockActionOutput,
) -> None:
    """A `success: false` search answer is logged and treated as an empty result
    (the behaviour the action had before the connector fix)."""
    set_is_first_run_to_true()
    google_threat_intelligence_product.set_asm_search_error("Search failed")

    SearchASMEntities("NAME").run()

    assert len(get_search_requests(script_session)) == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value
    assert action_output.results.output_message == NO_ENTITIES_MESSAGE
