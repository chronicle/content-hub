from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions.GetGroupDetails import GetGroupDetails
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"

ACTION_PARAMETERS: dict[str, str] = {
    "Group Email Addresses": GROUP_EMAIL,
}

MOCK_GROUP_DATA: dict = {
    "id": "grp-id-123",
    "email": GROUP_EMAIL,
    "name": "My Group",
    "description": "Test group description",
    "kind": "admin#directory#group",
    "adminCreated": True,
    "directMembersCount": "5",
}

MOCK_GROUP_SETTINGS: dict = {
    "kind": "groupsSettings#groups",
    "email": GROUP_EMAIL,
    "name": "My Group",
    "whoCanJoin": "INVITED_CAN_JOIN",
    "whoCanViewMembership": "ALL_MEMBERS_CAN_VIEW",
    "whoCanPostMessage": "ALL_MEMBERS_CAN_POST",
    "isArchived": "false",
    "membersCanPostAsTheGroup": "false",
}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully enriched the following groups using information "
    f"from Google Workspace: {GROUP_EMAIL}\n"
)
NONE_ENRICHED_OUTPUT_MESSAGE: str = "None of the groups were enriched.\n"

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_get_group_details_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_settings(GROUP_EMAIL, MOCK_GROUP_SETTINGS)

    GetGroupDetails().run()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_get_group_details_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # Neither group nor settings seeded → API returns 404
    GetGroupDetails().run()

    assert len(script_session.request_history) > 0
    assert NONE_ENRICHED_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_get_group_details_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    GetGroupDetails().run()

    assert action_output.results.execution_state == ExecutionState.FAILED
