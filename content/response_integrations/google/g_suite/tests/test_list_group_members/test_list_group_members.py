from __future__ import annotations

import json

from TIPCommon.base.action import ExecutionState

from g_suite.actions import ListGroupMembers
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"

ACTION_PARAMETERS: dict[str, str | bool] = {
    "Group Email Address": GROUP_EMAIL,
    "Include Derived Membership": True,
}

MOCK_GROUP_DATA: dict = {
    "id": "grp-id-123",
    "email": GROUP_EMAIL,
    "name": "My Group",
    "kind": "admin#directory#group",
}

MOCK_MEMBERS: list[dict] = [
    {
        "kind": "admin#directory#member",
        "email": "member1@domain.com",
        "role": "MEMBER",
        "type": "USER",
        "status": "ACTIVE",
        "id": "mem-id-1",
    },
    {
        "kind": "admin#directory#member",
        "email": "member2@domain.com",
        "role": "OWNER",
        "type": "USER",
        "status": "ACTIVE",
        "id": "mem-id-2",
    },
]

SUCCESS_OUTPUT_MESSAGE: str = "Successfully fetched group members."

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_members_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_members(GROUP_EMAIL, MOCK_MEMBERS)

    ListGroupMembers.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value == json.dumps(MOCK_MEMBERS)
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_members_empty(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    # Group seeded but no members — mock returns HTTP 200 with empty list.
    # ISSUE FINDER: The mock returns 200 with empty members for any registered
    # group_email, so there is no way to trigger GSuiteNotFoundException from
    # list_group_members without removing the group from the product entirely.
    # An unregistered group_email also returns 200 with empty list (default dict).
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_members(GROUP_EMAIL, [])

    ListGroupMembers.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value == json.dumps([])
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_list_group_members_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    ListGroupMembers.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
