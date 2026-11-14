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

"""Tests for the Lock SAP User, Delete User Session, and Activate Audit Log actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from sap_erp.actions import activate_audit_log, delete_user_session, lock_sap_user
from sap_erp.core.constants import (
    ACTIVATE_AUDIT_LOG_FUNCTION_ID,
    ACTIVATE_AUDIT_LOG_SCRIPT_NAME,
    DELETE_USER_SESSION_FUNCTION_ID,
    DELETE_USER_SESSION_SCRIPT_NAME,
    LOCK_SAP_USER_SCRIPT_NAME,
    SAP_CLIENT_NUMBER_PARAM,
    SAP_INSTANCE_NAME_PARAM,
    SAP_USERNAME_PARAM,
    USER_LOCK_FUNCTION_ID,
)
from sap_erp.core.exceptions import SapErpAuthError
from sap_erp.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from collections.abc import Callable

    from integration_testing.platform.script_output import MockActionOutput

    from .conftest import ResponseFactory

INSTANCE = "S4H_SANDBOX_00"
CLIENT = "100"


@dataclass(frozen=True)
class ActionCase:
    """Specification of one SAP ERP RFC action for parametrized tests."""

    main_fn: Callable[[], None]
    action_name: str
    function_id: str
    extra_params: dict[str, str]
    payload: dict[str, Any]
    success_message: str
    sap_failure_prefix: str


CASES = [
    pytest.param(
        ActionCase(
            main_fn=lock_sap_user.main,
            action_name=LOCK_SAP_USER_SCRIPT_NAME,
            function_id=USER_LOCK_FUNCTION_ID,
            extra_params={SAP_USERNAME_PARAM: "SAPUSER1"},
            payload={"username": "SAPUSER1"},
            success_message="Successfully locked user SAPUSER1.",
            sap_failure_prefix="Failed to lock user SAPUSER1. SAP Error: ",
        ),
        id="lock_sap_user",
    ),
    pytest.param(
        ActionCase(
            main_fn=delete_user_session.main,
            action_name=DELETE_USER_SESSION_SCRIPT_NAME,
            function_id=DELETE_USER_SESSION_FUNCTION_ID,
            extra_params={SAP_USERNAME_PARAM: "SAPUSER1"},
            payload={"username": "SAPUSER1", "client": CLIENT},
            success_message="Successfully deleted user session for SAPUSER1.",
            sap_failure_prefix="Failed to delete user session for SAPUSER1. SAP Error: ",
        ),
        id="delete_user_session",
    ),
    pytest.param(
        ActionCase(
            main_fn=activate_audit_log.main,
            action_name=ACTIVATE_AUDIT_LOG_SCRIPT_NAME,
            function_id=ACTIVATE_AUDIT_LOG_FUNCTION_ID,
            extra_params={},
            payload={},
            success_message="Successfully activated SAP audit log.",
            sap_failure_prefix="Failed to activate audit log. SAP Error: ",
        ),
        id="activate_audit_log",
    ),
]


def _run_case(
    case: ActionCase,
    *,
    client: str = CLIENT,
) -> None:
    params = {
        SAP_INSTANCE_NAME_PARAM: INSTANCE,
        SAP_CLIENT_NUMBER_PARAM: client,
        **case.extra_params,
    }

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=params)
    def _invoke() -> None:
        case.main_fn()

    _invoke()


def assert_failed(
    action_output: MockActionOutput,
    case: ActionCase,
    expected_reason: str,
) -> None:
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    expected_prefix = f'Error executing action "{case.action_name}"\nReason: '
    assert action_output.results.output_message.startswith(expected_prefix)
    assert expected_reason in action_output.results.output_message


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_calls_gateway_with_expected_arguments(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
) -> None:
    mock_execute.return_value = make_response(200, {"status": "SUCCESS"})

    _run_case(case)

    mock_execute.assert_called_once_with(
        function_id=case.function_id,
        sap_instance=INSTANCE,
        sap_client=CLIENT,
        payload=case.payload,
    )


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_success(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    body = {"status": "SUCCESS", "functionId": case.function_id}
    mock_execute.return_value = make_response(200, body)

    _run_case(case)

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.output_message == case.success_message
    assert action_output.results.json_output.json_result == body


@pytest.mark.parametrize("invalid_client", ["10", "1000", "ABC", "12A"])
@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_invalid_sap_client_number_rejected_before_gateway_call(
    mock_execute: MagicMock,
    case: ActionCase,
    invalid_client: str,
    action_output: MockActionOutput,
) -> None:
    _run_case(case, client=invalid_client)

    mock_execute.assert_not_called()
    assert_failed(
        action_output,
        case,
        f"SAP Client Number must be a 3-digit numeric string (got '{invalid_client}').",
    )


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_http_error_surfaces_gateway_error_field(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    mock_execute.return_value = make_response(
        500, {"error": "SAP instance not configured: BAD"}
    )

    _run_case(case)

    assert_failed(
        action_output,
        case,
        "Proxy request failed (HTTP 500): SAP instance not configured: BAD",
    )
    assert action_output.results.json_output is None


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_http_error_plain_text_body(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    mock_execute.return_value = make_response(502, text="Bad Gateway")

    _run_case(case)

    assert_failed(action_output, case, "Proxy request failed (HTTP 502): Bad Gateway")


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_auth_error(
    mock_execute: MagicMock,
    case: ActionCase,
    action_output: MockActionOutput,
) -> None:
    mock_execute.side_effect = SapErpAuthError("token fetch failed")

    _run_case(case)

    assert_failed(action_output, case, "Authentication error: token fetch failed")


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_network_error(
    mock_execute: MagicMock,
    case: ActionCase,
    action_output: MockActionOutput,
) -> None:
    mock_execute.side_effect = requests.exceptions.ConnectTimeout("timed out")

    _run_case(case)

    assert_failed(
        action_output,
        case,
        "Failed to communicate with SAP RFC Gateway: timed out",
    )


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_non_json_success_response(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    mock_execute.return_value = make_response(200, text="<html>ok</html>")

    _run_case(case)

    assert_failed(
        action_output,
        case,
        "Received unexpected non-JSON response: <html>ok</html>",
    )
    assert action_output.results.json_output is None


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_sap_bapiret2_error_messages_joined(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    body = {
        "status": "ERROR",
        "return": [
            {"type": "E", "message": "User SAPUSER1 does not exist"},
            {"type": "E", "message": "No changes made"},
        ],
    }
    mock_execute.return_value = make_response(200, body)

    _run_case(case)

    assert_failed(
        action_output,
        case,
        f"{case.sap_failure_prefix}User SAPUSER1 does not exist; No changes made",
    )
    # The SAP response payload is still attached to the action result for debugging.
    assert action_output.results.json_output.json_result == body


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_sap_error_falls_back_to_error_field_when_return_is_null(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    body = {"status": "ERROR", "return": None, "error": "RFC communication failure"}
    mock_execute.return_value = make_response(200, body)

    _run_case(case)

    assert_failed(
        action_output,
        case,
        f"{case.sap_failure_prefix}RFC communication failure",
    )


@pytest.mark.parametrize("case", CASES)
@patch("sap_erp.core.sap_erp_manager.SapErpManager.execute_function")
def test_sap_error_falls_back_to_unexpected_status(
    mock_execute: MagicMock,
    case: ActionCase,
    make_response: ResponseFactory,
    action_output: MockActionOutput,
) -> None:
    body = {"status": "UNKNOWN"}
    mock_execute.return_value = make_response(200, body)

    _run_case(case)

    assert_failed(
        action_output,
        case,
        f"{case.sap_failure_prefix}Unexpected SAP status: UNKNOWN",
    )
