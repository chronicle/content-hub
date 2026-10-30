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

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch

import pytest
import requests
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import AssignCaseToUser


@set_metadata(
    integration_config={},
    parameters={
        "Case Id": "8",
        "Assign To": "@Admin",
        "Alert Id": "alert_1",
    },
)
@patch.object(AssignCaseToUser, "assign_case_to_user")
def test_assign_case_to_user_success_empty_204_response(
    mock_assign: MagicMock,
    action_output: MockActionOutput,
) -> None:
    """Verify successful assignment sets clear output message and populates JsonResult."""
    mock_assign.return_value = []

    AssignCaseToUser.main()

    mock_assign.assert_called_once_with(
        chronicle_soar=ANY,
        case_id="8",
        assign_to="@Admin",
        alert_identifier="alert_1",
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == "Successfully assigned case 8 to @Admin."
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "caseId": "8",
        "assignedTo": "@Admin",
    }


@set_metadata(
    integration_config={},
    parameters={
        "Case Id": "42",
        "Assign To": "user-uuid-123",
        "Alert Id": "alert_1",
    },
)
@patch.object(AssignCaseToUser, "assign_case_to_user")
def test_assign_case_to_user_success_with_api_payload(
    mock_assign: MagicMock,
    action_output: MockActionOutput,
) -> None:
    """Verify non-empty API response data is included in JsonResult."""
    mock_assign.return_value = {"updatedCases": [42]}

    AssignCaseToUser.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == "Successfully assigned case 42 to user-uuid-123."
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "caseId": "42",
        "assignedTo": "user-uuid-123",
        "response": {"updatedCases": [42]},
    }


@pytest.mark.parametrize(
    ("status_code", "error_body"),
    [
        (400, '{"errorCode":2000,"errorMessage":"Cannot assign case to disabled user account."}'),
        (403, '{"error":{"code":403,"message":"Permission chronicle.cases.update denied"}}'),
        (500, '{"error":{"code":500,"message":"Internal error"}}'),
    ],
)
@set_metadata(
    integration_config={},
    parameters={
        "Case Id": "8",
        "Assign To": "tjones@example.com",
        "Alert Id": "id",
    },
)
@patch("TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api", return_value=True)
@patch("TIPCommon.utils.platform_supports_1p_api", return_value=True)
def test_assign_case_to_user_1p_http_error_fails_cleanly_with_body(
    _mock_utils_1p: MagicMock,
    _mock_factory_1p: MagicMock,
    status_code: int,
    error_body: str,
    action_output: MockActionOutput,
) -> None:
    """Verify 1P HTTP errors set FAILED state, False result, and include the API error body."""
    err_resp = requests.Response()
    err_resp.status_code = status_code
    err_resp.reason = "Error"
    err_resp.url = (
        "https://soar.example.com/v1alpha/projects/p/locations/us/instances/i/"
        "cases:executeBulkAssign"
    )
    err_resp._content = error_body.encode()

    with patch(
        "TIPCommon.rest.soar_platform_clients.base_soar_api.BaseSoarApi._make_request",
        return_value=err_resp,
    ):
        AssignCaseToUser.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "Error executing action 'AssignCaseToUser'." in action_output.results.output_message
    assert str(status_code) in action_output.results.output_message
    assert error_body in action_output.results.output_message
    assert action_output.results.json_output is None
