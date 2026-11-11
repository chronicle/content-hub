from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import AddMembersToGroup
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"
MEMBER_EMAIL: str = "newmember@domain.com"

ACTION_PARAMETERS: dict[str, str] = {
    "Group Email Address": GROUP_EMAIL,
    "User Email Addresses": MEMBER_EMAIL,
}

MOCK_GROUP_DATA: dict = {
    "id": "grp-id-123",
    "email": GROUP_EMAIL,
    "name": "My Group",
    "kind": "admin#directory#group",
}

SUCCESS_OUTPUT_MESSAGE_FRAGMENT: str = "The following users were added to the group:"
EXISTING_MEMBER_MESSAGE_FRAGMENT: str = "The following members already exist in group:"

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_add_members_to_group_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_members(GROUP_EMAIL, [])

    AddMembersToGroup.main()

    assert len(script_session.request_history) > 0
    assert SUCCESS_OUTPUT_MESSAGE_FRAGMENT in action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None
    # Verify the member was added to the product
    members = product.get_group_members(GROUP_EMAIL)
    assert any(m.get("email") == MEMBER_EMAIL for m in members)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_add_members_to_group_already_exists(
    _script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    # Pre-seed the member so the mock returns 409 Conflict
    product.set_group_members(
        GROUP_EMAIL,
        [{"email": MEMBER_EMAIL, "role": "MEMBER", "kind": "admin#directory#member"}],
    )

    AddMembersToGroup.main()

    assert EXISTING_MEMBER_MESSAGE_FRAGMENT in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_add_members_to_group_group_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No group seeded → 404 on POST → generic Exception → failed_entities
    AddMembersToGroup.main()

    assert len(script_session.request_history) > 0
    assert "Action failed to add the following members to group:" in action_output.results.output_message
    # ISSUE FINDER: AddMembersToGroup does NOT set result_value=False when the
    # group is not found; result_value stays True because it is set before the loop.
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_add_members_to_group_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    AddMembersToGroup.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
