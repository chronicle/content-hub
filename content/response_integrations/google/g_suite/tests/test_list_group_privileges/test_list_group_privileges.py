from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions.ListGroupPrivileges import ListGroupPrivileges
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"
ROLE_ID: str = "role123"

ACTION_PARAMETERS: dict[str, str | int | bool] = {
    "Group Email Addresses": GROUP_EMAIL,
    "Max Roles To Return": 50,
    "Max Privileges To Return": 50,
    "Expand Privileges": False,
}

MOCK_GROUP_DATA: dict = {
    "id": "grp-id-123",
    "email": GROUP_EMAIL,
    "name": "My Group",
    "kind": "admin#directory#group",
}

MOCK_ROLE_ASSIGNMENT: dict = {
    "roleAssignmentId": "ra-id-1",
    "roleId": ROLE_ID,
    "assignedTo": "grp-id-123",
    "scopeType": "CUSTOMER",
}

MOCK_ROLE: dict = {
    "roleId": ROLE_ID,
    "roleName": "MockRole",
    "roleDescription": "A mock role",
    "rolePrivileges": [
        {"serviceId": "svc1", "privilegeName": "READ_ACCESS"},
    ],
    "isSystemRole": False,
    "isSuperAdminRole": False,
}

SUCCESS_OUTPUT_MESSAGE_FRAGMENT: str = (
    "Successfully fetched information for the following groups"
)
NONE_FOUND_OUTPUT_MESSAGE: str = (
    "No information was found for the provided groups in Google Workspace.\n"
)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_privileges_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_role_assignments(MOCK_GROUP_DATA["id"], [MOCK_ROLE_ASSIGNMENT])
    product.set_role(ROLE_ID, MOCK_ROLE)

    ListGroupPrivileges().run()

    assert len(script_session.request_history) > 0
    assert SUCCESS_OUTPUT_MESSAGE_FRAGMENT in action_output.results.output_message
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_privileges_group_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No group seeded → get_group returns 404 → not_found_groups
    ListGroupPrivileges().run()

    assert len(script_session.request_history) > 0
    assert NONE_FOUND_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_privileges_no_roles(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    # Group exists but has no role assignments
    product.set_group(GROUP_EMAIL, MOCK_GROUP_DATA)
    product.set_role_assignments(MOCK_GROUP_DATA["id"], [])

    ListGroupPrivileges().run()

    assert len(script_session.request_history) > 0
    # No roles → groups_with_no_filtered_roles
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_group_privileges_api_error(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    bad_config = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}

    @set_metadata(integration_config=bad_config, parameters=ACTION_PARAMETERS)
    def _run(
        _ss: ApiSession,
        __p: Product,
        _ao: MockActionOutput,
    ) -> None:
        ListGroupPrivileges().run()
        assert _ao.results.execution_state == ExecutionState.FAILED

    _run(script_session, _product, action_output)
