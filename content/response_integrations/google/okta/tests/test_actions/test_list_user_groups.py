from __future__ import annotations

import json
from http import HTTPStatus
from typing import TYPE_CHECKING

from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from okta.actions import ListRoles, ListUserGroups
from okta.tests.common import CONFIG_PATH
from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from okta.tests.core.product import Product
    from okta.tests.core.session import Session
    from integration_testing.platform.script_output import MockActionOutput

USER_ID = "00u1a2b3c4d5e6f7g8h9"
USER_NOT_FOUND = "not.found@example.com"
SCOPE_USER_LOGIN = "SCOPE.USER@EXAMPLE.COM"
USER_GROUPS_PATH = f"/api/v1/users/{USER_ID}/groups"
OKTA_PAGE_SIZE = 200
RATE_LIMIT_ERROR = {
    "errorCode": "E0000047",
    "errorSummary": "API call exceeded rate limit due to too many requests.",
    "errorCauses": [],
}


def _build_groups(start: int, count: int) -> list[SingleJson]:
    """Build ``count`` unique Okta group objects starting from ``start``."""
    return [
        {
            "id": f"00g{index:017d}",
            "type": "OKTA_GROUP",
            "profile": {
                "name": f"Group {index}",
                "description": f"Test group {index}",
            },
        }
        for index in range(start, start + count)
    ]


def _get_group_ids(action_output: MockActionOutput, user_key: str) -> list[str]:
    """Extract the group IDs returned for ``user_key`` from the action result."""
    result_value = json.loads(action_output.results.result_value)
    return [group["id"] for group in result_value.get(user_key, [])]


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_follows_next_link_for_more_than_one_page(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Regression test for b/568241264: 272 groups must not be capped at 200."""
    first_page = _build_groups(start=0, count=OKTA_PAGE_SIZE)
    second_page = _build_groups(start=OKTA_PAGE_SIZE, count=72)
    okta_product.set_user_groups_pages(
        USER_ID,
        [(HTTPStatus.OK, first_page), (HTTPStatus.OK, second_page)],
    )

    ListUserGroups.main()

    assert len(script_session.request_history) == 2
    first_request = script_session.request_history[0].request
    second_request = script_session.request_history[1].request
    assert first_request.url.path == USER_GROUPS_PATH
    assert "after" not in first_request.params
    assert second_request.url.path == USER_GROUPS_PATH
    assert second_request.params["after"] == ["1"]

    group_ids = _get_group_ids(action_output, USER_ID)
    assert len(group_ids) == 272
    assert len(set(group_ids)) == 272
    assert group_ids == [group["id"] for group in first_page + second_page]

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        f"The user with id {USER_ID} belongs to 272 groups"
        in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_collects_all_pages_when_there_are_many(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify ListUserGroups collects items across four pages in order."""
    pages = [
        (HTTPStatus.OK, _build_groups(start=0, count=OKTA_PAGE_SIZE)),
        (HTTPStatus.OK, _build_groups(start=OKTA_PAGE_SIZE, count=OKTA_PAGE_SIZE)),
        (HTTPStatus.OK, _build_groups(start=2 * OKTA_PAGE_SIZE, count=OKTA_PAGE_SIZE)),
        (HTTPStatus.OK, _build_groups(start=3 * OKTA_PAGE_SIZE, count=50)),
    ]
    okta_product.set_user_groups_pages(USER_ID, pages)

    ListUserGroups.main()

    assert len(script_session.request_history) == 4
    assert [
        record.request.params.get("after", ["0"])[0]
        for record in script_session.request_history
    ] == ["0", "1", "2", "3"]

    expected_total = 3 * OKTA_PAGE_SIZE + 50
    group_ids = _get_group_ids(action_output, USER_ID)
    assert len(group_ids) == expected_total
    assert len(set(group_ids)) == expected_total
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        f"The user with id {USER_ID} belongs to {expected_total} groups"
        in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_single_page_without_next_link(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify ListUserGroups stops after one request when no next link is present."""
    only_page = _build_groups(start=0, count=OKTA_PAGE_SIZE)
    okta_product.set_user_groups_pages(USER_ID, [(HTTPStatus.OK, only_page)])

    ListUserGroups.main()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == USER_GROUPS_PATH

    group_ids = _get_group_ids(action_output, USER_ID)
    assert len(group_ids) == OKTA_PAGE_SIZE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        f"The user with id {USER_ID} belongs to {OKTA_PAGE_SIZE} groups"
        in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_user_without_groups(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify ListUserGroups reports when a user belongs to no groups."""
    okta_product.set_user_groups_pages(USER_ID, [(HTTPStatus.OK, [])])

    ListUserGroups.main()

    assert len(script_session.request_history) == 1
    assert json.loads(action_output.results.result_value) == {}
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "No groups were found" in action_output.results.output_message
    assert "doesn't belong to any group" in action_output.results.output_message


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_error_on_subsequent_page_is_reported(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify ListUserGroups surfaces an HTTP error from a subsequent page."""
    first_page = _build_groups(start=0, count=OKTA_PAGE_SIZE)
    okta_product.set_user_groups_pages(
        USER_ID,
        [
            (HTTPStatus.OK, first_page),
            (HTTPStatus.TOO_MANY_REQUESTS, RATE_LIMIT_ERROR),
        ],
    )

    ListUserGroups.main()

    assert len(script_session.request_history) == 2
    assert json.loads(action_output.results.result_value) == {}
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "No groups were found" in action_output.results.output_message
    assert (
        RATE_LIMIT_ERROR["errorSummary"] in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_NOT_FOUND,
        "Also Run On Scope": "false",
    },
)
def test_list_user_groups_user_not_found(
    script_session: Session,
    action_output: MockActionOutput,
) -> None:
    """Verify ListUserGroups reports a 404 error when the user does not exist."""
    ListUserGroups.main()

    assert len(script_session.request_history) == 1
    assert json.loads(action_output.results.result_value) == {}
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert "No groups were found" in action_output.results.output_message
    assert (
        f"Not found: Resource not found: {USER_NOT_FOUND} (User)"
        in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": "",
        "Also Run On Scope": "true",
    },
    entities=[create_entity(SCOPE_USER_LOGIN, EntityTypesEnum.USER)],
)
def test_list_user_groups_on_scope_follows_next_link(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify scope execution follows rel="next" using an upper-cased entity login."""
    first_page = _build_groups(start=0, count=OKTA_PAGE_SIZE)
    second_page = _build_groups(start=OKTA_PAGE_SIZE, count=72)
    okta_product.set_user_groups_pages(
        SCOPE_USER_LOGIN,
        [(HTTPStatus.OK, first_page), (HTTPStatus.OK, second_page)],
    )

    ListUserGroups.main()

    assert len(script_session.request_history) == 2
    assert all(
        record.request.url.path == f"/api/v1/users/{SCOPE_USER_LOGIN}/groups"
        for record in script_session.request_history
    )

    group_ids = _get_group_ids(action_output, SCOPE_USER_LOGIN)
    assert len(group_ids) == 272
    assert len(set(group_ids)) == 272
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        f'The user "{SCOPE_USER_LOGIN}" belongs to 272 groups'
        in action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_list_roles_follows_next_link(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify ListRoles collects roles across pages via _get_all_pages."""
    first_page: list[SingleJson] = [{"id": "IFIFAX25", "type": "USER_ADMIN"}]
    second_page: list[SingleJson] = [{"id": "JGJGBY36", "type": "APP_ADMIN"}]
    okta_product.set_user_roles_pages(
        USER_ID,
        [(HTTPStatus.OK, first_page), (HTTPStatus.OK, second_page)],
    )

    ListRoles.main()

    assert len(script_session.request_history) == 2
    result_value = json.loads(action_output.results.result_value)
    assert [role["type"] for role in result_value[USER_ID]] == [
        "USER_ADMIN",
        "APP_ADMIN",
    ]
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        f"The user with id {USER_ID} has 2 roles: USER_ADMIN, APP_ADMIN"
        in action_output.results.output_message
    )
