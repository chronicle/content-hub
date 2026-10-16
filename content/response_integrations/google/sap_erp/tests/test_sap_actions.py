# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared behaviour tests for the three SAP RFC actions.

Each action posts one RFC call through SapErpManager and maps the gateway
response to result_value / execution_state / output_message the same way, so
the cases are parametrized over every action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest
import requests
from TIPCommon.base.action import Action, ExecutionState

from sap_erp.actions.activate_audit_log import ActivateAuditLogAction
from sap_erp.actions.delete_user_session import DeleteUserSessionAction
from sap_erp.actions.lock_sap_user import LockSapUserAction
from sap_erp.core.sap_erp_manager import SapErpAuthError

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from .conftest import ResponseFactory

pytestmark = pytest.mark.usefixtures("mock_soar_action")

INSTANCE = "S4H_SANDBOX_00"
CLIENT = "100"
USERNAME = "JDOE"


@dataclass
class ActionCase:
    action_cls: type[Action]
    name: str
    function_id: str
    payload: dict[str, Any]
    success_message: str
    failure_prefix: str
    attrs: dict[str, str] = field(default_factory=dict)


CASES = [
    ActionCase(
        action_cls=ActivateAuditLogAction,
        name="Activate Audit Log",
        function_id="ACTIVATE_AUDIT_LOG",
        payload={},
        success_message="Successfully activated SAP audit log.",
        failure_prefix="Failed to activate audit log.",
    ),
    ActionCase(
        action_cls=LockSapUserAction,
        name="Lock SAP User",
        function_id="USER_LOCK",
        payload={"username": USERNAME},
        success_message=f"Successfully locked user {USERNAME}.",
        failure_prefix=f"Failed to lock user {USERNAME}.",
        attrs={"sap_username": USERNAME},
    ),
    ActionCase(
        action_cls=DeleteUserSessionAction,
        name="Delete User Session",
        function_id="DELETE_USER_SESSION",
        # TH_DELETE_USER takes CLIENT as an import parameter, so it must be in
        # the inner payload, not only on the envelope.
        payload={"username": USERNAME, "client": CLIENT},
        success_message=f"Successfully deleted user session for {USERNAME}.",
        failure_prefix=f"Failed to delete user session for {USERNAME}.",
        attrs={"sap_username": USERNAME},
    ),
]


@pytest.fixture(params=CASES, ids=lambda c: c.name)
def case(request: pytest.FixtureRequest) -> ActionCase:
    """Provide each SAP action's expectations in turn.

    Returns:
        The current ActionCase.

    """
    return request.param


def build_action(case: ActionCase, manager: MagicMock) -> Action:
    action = case.action_cls(name=case.name)
    action._api_client = manager
    action.cloud_run_url = "https://gw-abc.a.run.app"
    action.sap_client_number = CLIENT
    action.sap_instance_name = INSTANCE
    for key, value in case.attrs.items():
        setattr(action, key, value)
    return action


def assert_failed(action: Action, message_substring: str) -> None:
    assert action.result_value is False
    assert action.execution_state == ExecutionState.FAILED
    assert message_substring in action.output_message


def test_sends_expected_rfc_call(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    manager.execute_function.return_value = make_response(200, {"status": "SUCCESS"})
    action = build_action(case, manager)

    action._perform_action()

    manager.execute_function.assert_called_once_with(
        function_id=case.function_id,
        sap_instance=INSTANCE,
        sap_client=CLIENT,
        payload=case.payload,
    )


def test_success(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    body = {"status": "SUCCESS", "functionId": case.function_id}
    manager.execute_function.return_value = make_response(200, body)
    action = build_action(case, manager)

    action._perform_action()

    assert action.result_value is True
    assert action.execution_state == ExecutionState.COMPLETED
    assert action.output_message == case.success_message
    action.soar_action.result.add_result_json.assert_called_once_with(body)


def test_http_error_surfaces_gateway_error_field(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    manager.execute_function.return_value = make_response(
        500, {"error": "SAP instance not configured: BAD"}
    )
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(
        action, "Proxy request failed (HTTP 500): SAP instance not configured: BAD"
    )
    action.soar_action.result.add_result_json.assert_not_called()


def test_http_error_plain_text_body(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    manager.execute_function.return_value = make_response(502, text="Bad Gateway")
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, "Proxy request failed (HTTP 502): Bad Gateway")


def test_auth_error(case: ActionCase, manager: MagicMock) -> None:
    manager.execute_function.side_effect = SapErpAuthError("token fetch failed")
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, "Authentication error: token fetch failed")


def test_network_error(case: ActionCase, manager: MagicMock) -> None:
    manager.execute_function.side_effect = requests.exceptions.ConnectTimeout(
        "timed out"
    )
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, "Failed to communicate with SAP RFC Gateway: timed out")


def test_non_json_success_response(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    manager.execute_function.return_value = make_response(200, text="<html>ok</html>")
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, "Received unexpected non-JSON response: <html>ok</html>")
    action.soar_action.result.add_result_json.assert_not_called()


def test_sap_error_joins_return_messages(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    body = {
        "status": "ERROR",
        "return": [
            {"type": "E", "message": "User JDOE does not exist"},
            {"type": "E", "message": "Second problem"},
            "not-a-dict-is-ignored",
        ],
    }
    manager.execute_function.return_value = make_response(200, body)
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(
        action,
        f"{case.failure_prefix} SAP Error: User JDOE does not exist; Second problem",
    )
    # The raw SAP response is still attached for the analyst.
    action.soar_action.result.add_result_json.assert_called_once_with(body)


def test_sap_error_falls_back_to_error_field(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    manager.execute_function.return_value = make_response(
        200, {"status": "ERROR", "error": "RFC_ERROR_SYSTEM_FAILURE"}
    )
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, "SAP Error: RFC_ERROR_SYSTEM_FAILURE")


def test_sap_error_with_null_return_list(
    case: ActionCase, manager: MagicMock, make_response: ResponseFactory
) -> None:
    # A present-but-null "return" must not raise TypeError.
    manager.execute_function.return_value = make_response(
        200, {"status": "ERROR", "return": None, "error": "Locked by admin"}
    )
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, f"{case.failure_prefix} SAP Error: Locked by admin")


@pytest.mark.parametrize("body", [{"status": "WARNING"}, {}], ids=["warning", "missing"])
def test_unexpected_status_is_failure(
    case: ActionCase,
    manager: MagicMock,
    make_response: ResponseFactory,
    body: dict[str, str],
) -> None:
    manager.execute_function.return_value = make_response(200, body)
    action = build_action(case, manager)

    action._perform_action()

    assert_failed(action, f"Unexpected SAP status: {body.get('status')}")


@pytest.mark.parametrize("verify_ssl", [True, False])
def test_init_api_clients_passes_verify_ssl(
    case: ActionCase, *, verify_ssl: bool
) -> None:
    action = case.action_cls(name=case.name)
    action.cloud_run_url = "https://gw-abc.a.run.app"
    action.verify_ssl = verify_ssl

    manager = action._init_api_clients()

    assert manager.cloud_run_url == "https://gw-abc.a.run.app"
    assert manager.verify_ssl is verify_ssl
