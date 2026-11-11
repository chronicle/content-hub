from __future__ import annotations

import pytest
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput

from google_threat_intelligence.actions import execute_ioc_search
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

NO_PARAMS_ERROR_MESSAGE = (
    "Failed during parameter extraction, Error: "
    "Missing mandatory parameter Search Query\n"
)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_no_input_params_error() -> None:

    with pytest.raises(Exception) as error:
        execute_ioc_search.main()

    assert type(error.value).__name__ == "ParameterExtractionError"
    assert str(error.value) == NO_PARAMS_ERROR_MESSAGE


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Search Query": "some_query",
    },
)
def test_no_result_query(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:

    execute_ioc_search.main()

    assert len(script_session.request_history) == 2
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/intelligence/search"
    )
    assert action_output.results == ActionOutput(
        output_message=execute_ioc_search.NO_RESULT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Search Query": "tag=crypto", "Max Results To Return": 3},
)
def test_success_result_query(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    success_search_response,
    get_item_response,
) -> None:

    google_threat_intelligence_product.add_search_query_response(
        response=success_search_response
    )
    execute_ioc_search.main()

    assert len(script_session.request_history) == 2
    assert (script_session.request_history[0].request.url.path ==
            "/api/v3/metadata")
    assert (
        script_session.request_history[1].request.url.path
        == "/api/v3/intelligence/search"
    )
    assert action_output.results == ActionOutput(
        output_message=execute_ioc_search.SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(
            title="JsonResult",
            content="",
            type=None,
            is_for_entity=False,
            json_result=[get_item_response],
        ),
        debug_output="",
    )


HIGH_VALUE = 500
ERROR_OUTPUT_MESSAGE = (
    "Error executing action GoogleThreatIntelligence - Execute IOC Search.\n"
    'Reason: Invalid parameter "Max Results To Return". '
    f"The value can't be greater then 200. Wrong value provided: {HIGH_VALUE}"
)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Search Query": "tag=crypto", "Max Results To Return": 500},
)
def test_failed_max_results_to_return(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    success_search_response,
) -> None:

    google_threat_intelligence_product.add_search_query_response(
        response=success_search_response
    )
    execute_ioc_search.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == ActionOutput(
        output_message=ERROR_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
        debug_output="",
    )
