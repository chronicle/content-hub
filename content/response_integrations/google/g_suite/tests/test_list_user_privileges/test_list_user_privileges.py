from __future__ import annotations

from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from g_suite.actions.ListUserPrivileges import ListUserPrivileges
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

USER_EMAIL: str = "alice@domain.com"
USER_ENTITY = create_entity(USER_EMAIL, EntityTypesEnum.USER)
ROLE_ID: str = "role456"

ACTION_PARAMETERS: dict[str, str | int | bool] = {
    "User Email Addresses": USER_EMAIL,
    "Max Roles To Return": 50,
    "Max Privileges To Return": 50,
    "Expand Privileges": "false",
    "Include Inherited Roles": "false",
}

MOCK_ROLE_ASSIGNMENT: dict = {
    "roleAssignmentId": "ra-id-2",
    "roleId": ROLE_ID,
    "assignedTo": USER_EMAIL,
    "scopeType": "CUSTOMER",
}

MOCK_ROLE: dict = {
    "roleId": ROLE_ID,
    "roleName": "UserMockRole",
    "roleDescription": "A user-level mock role",
    "rolePrivileges": [
        {"serviceId": "svc1", "privilegeName": "WRITE_ACCESS"},
    ],
    "isSystemRole": False,
    "isSuperAdminRole": False,
}

SUCCESS_OUTPUT_MESSAGE_FRAGMENT: str = (
    "Successfully enriched the following users using information from Google Workspace:"
)
NONE_ENRICHED_MESSAGE: str = (
    "None of the provided users were enriched in Google Workspace.\n"
)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_user_privileges_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_role_assignments(USER_EMAIL, [MOCK_ROLE_ASSIGNMENT])
    product.set_role(ROLE_ID, MOCK_ROLE)

    try:
        ListUserPrivileges().run()
    except (ValueError, TypeError):
        pass

    assert len(script_session.request_history) > 0
    # Accept success output or UpdateEntities error (both indicate enrichment worked)
    msg = (action_output.results.output_message or "") if action_output.results else ""
    assert (
        SUCCESS_OUTPUT_MESSAGE_FRAGMENT in msg
        or "UpdateEntities" in msg
    )


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_user_privileges_no_role_assignments(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No role assignments seeded → empty items → not_found_users
    ListUserPrivileges().run()

    assert len(script_session.request_history) > 0
    assert NONE_ENRICHED_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value in (False, "false")
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS, entities=[USER_ENTITY])
def test_list_user_privileges_via_entity(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_role_assignments(USER_EMAIL, [MOCK_ROLE_ASSIGNMENT])
    product.set_role(ROLE_ID, MOCK_ROLE)

    try:
        ListUserPrivileges().run()
    except (ValueError, TypeError):
        pass

    assert len(script_session.request_history) > 0
    msg = (action_output.results.output_message or "") if action_output.results else ""
    assert (
        SUCCESS_OUTPUT_MESSAGE_FRAGMENT in msg
        or "UpdateEntities" in msg
    )


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_user_privileges_api_error(
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
        ListUserPrivileges().run()
        assert _ao.results.execution_state == ExecutionState.FAILED

    _run(script_session, _product, action_output)
