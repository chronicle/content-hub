from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts import (
    RunMicrosoftSearchQuery,
)

from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.integrations.MicrosoftGraphMailDelegated.conftest import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


ERROR_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Run Microsoft Search Query".'
    "\nReason: Failed to construct a search query based on the provided parameters. "
    "Please check, if you specified all parameters properly."
)
ERROR_MESSAGE2: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Run Microsoft Search Query".'
    "\nReason: Failed to run the search as the provided combination of entities to "
    "search by is not supported by the API. Please consult Microsoft Documentation "
    "for supported entity combinations - "
    "https://learn.microsoft.com/en-us/graph/search-concept-interleaving.\n"
    "Error is \"test\""
)
JSON_RESULT: list[dict] = [
    {
        "hitId": "abcd",
        "rank": 1,
        "summary": "mock summary",
        "resource": {
            "@odata.type": "#microsoft.graph.message",
            "createdDateTime": "2024-08-20T20:26:29Z",
        },
    }
]

SUCCESS_RETURN_QUERY_RESULT: ActionOutput = ActionOutput(
    output_message="Successfully retrieved results for the provided search query.",
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=ActionJsonOutput(
        title="JsonResult",
        content="",
        type=None,
        is_for_entity=False,
        json_result=JSON_RESULT,
    ),
)
FAILED_RETURN_QUERY_RESULT = ActionOutput(
    output_message=ERROR_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)
FAILED_INVALID_ENTITY_TYPE_RETURN_QUERY_RESULT = ActionOutput(
    output_message=ERROR_MESSAGE2,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)


@set_metadata(
    parameters={
        "Search in Mailbox": "Default Mailbox",
        "Entity Types To Search": "message",
        "Fields To Return": "",
        "Search Query": "Test",
        "Max Rows To Return": "2",
        "Advanced Query": "",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_run_microsoft_search_query_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)

    RunMicrosoftSearchQuery.RunMicrosoftSearchQuery().run()

    assert len(script_session.request_history) == 2
    assert action_output.results == SUCCESS_RETURN_QUERY_RESULT


@set_metadata(
    parameters={
        "Search in Mailbox": "Default Mailbox",
        "Entity Types To Search": "",
        "Fields To Return": "",
        "Search Query": "Test",
        "Max Rows To Return": "2",
        "Advanced Query": "",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_run_microsoft_search_query_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)

    RunMicrosoftSearchQuery.RunMicrosoftSearchQuery().run()

    assert len(script_session.request_history) == 1
    assert action_output.results == FAILED_RETURN_QUERY_RESULT


@set_metadata(
    parameters={
        "Search in Mailbox": "Default Mailbox",
        "Entity Types To Search": "test",
        "Fields To Return": "",
        "Search Query": "Test",
        "Max Rows To Return": "2",
        "Advanced Query": "",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_run_microsoft_search_invalid_entity_type_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)

    RunMicrosoftSearchQuery.RunMicrosoftSearchQuery().run()

    assert len(script_session.request_history) == 1
    assert action_output.results == FAILED_INVALID_ENTITY_TYPE_RETURN_QUERY_RESULT
