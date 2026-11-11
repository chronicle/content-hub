from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import RemoveMembersFromGroup
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"
MEMBER_EMAIL: str = "existing.member@domain.com"

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

SUCCESS_OUTPUT_MESSAGE_FRAGMENT: str = "The following users were removed from group:"
NOT_FOUND_MEMBER_FRAGMENT: str = "The following members were not found in group:"

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_remove_members_from_group_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_members(
        GROUP_EMAIL,
        [{"email": MEMBER_EMAIL, "role": "MEMBER", "kind": "admin#directory#member"}],
    )

    RemoveMembersFromGroup.main()

    assert len(script_session.request_history) > 0
    assert SUCCESS_OUTPUT_MESSAGE_FRAGMENT in action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    # Verify the member was removed from the product
    members = product.get_group_members(GROUP_EMAIL)
    assert not any(m.get("email") == MEMBER_EMAIL for m in members)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_remove_members_from_group_member_not_found(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    # Group exists but member does not
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_group_members(GROUP_EMAIL, [])

    RemoveMembersFromGroup.main()

    assert len(script_session.request_history) > 0
    assert NOT_FOUND_MEMBER_FRAGMENT in action_output.results.output_message
    # ISSUE FINDER: RemoveMembersFromGroup sets result_value=True at the top and
    # never resets it to False when members are not found.
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_remove_members_from_group_group_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No group seeded → 404 on DELETE → GSuiteNotFoundException → non_existing_entities
    RemoveMembersFromGroup.main()

    assert len(script_session.request_history) > 0
    assert NOT_FOUND_MEMBER_FRAGMENT in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_remove_members_from_group_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    RemoveMembersFromGroup.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
