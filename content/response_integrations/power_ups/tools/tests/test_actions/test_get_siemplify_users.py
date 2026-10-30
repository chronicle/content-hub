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

from ...actions import GetSiemplifyUsers


@set_metadata(
    integration_config={},
    parameters={"Hide Disabled Users": "true"},
)
@patch.object(GetSiemplifyUsers, "get_siemplify_user_details")
def test_get_siemplify_users_success(
    mock_get_users: MagicMock,
    action_output: MockActionOutput,
) -> None:
    """Verify successful lookup returns users JSON and COMPLETED state."""
    mock_user = MagicMock()
    mock_user.to_json.return_value = {
        "id": 1,
        "displayName": "user-uuid-1",
        "email": "analyst@example.com",
    }
    mock_get_users.return_value = [mock_user]

    GetSiemplifyUsers.main()

    mock_get_users.assert_called_once_with(
        chronicle_soar=ANY,
        search_term="",
        filter_by_role=False,
        requested_page=0,
        page_size=1000,
        should_hide_disabled_users=True,
    )
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == "Returned Siemplify Users."
    assert action_output.results.json_output is not None
    assert action_output.results.json_output.json_result == {
        "siemplifyUsers": [
            {
                "id": 1,
                "displayName": "user-uuid-1",
                "email": "analyst@example.com",
            }
        ]
    }


@pytest.mark.parametrize(
    ("status_code", "error_body"),
    [
        (403, '{"error":{"code":403,"message":"Permission chronicle.legacySoarUsers.get denied"}}'),
        (404, '{"error":{"code":404,"message":"Not found"}}'),
        (500, '{"error":{"code":500,"message":"Internal error"}}'),
    ],
)
@set_metadata(
    integration_config={},
    parameters={"Hide Disabled Users": "false"},
)
@patch("TIPCommon.rest.soar_platform_clients.api_client_factory.platform_supports_1p_api", return_value=True)
@patch("TIPCommon.utils.platform_supports_1p_api", return_value=True)
def test_get_siemplify_users_1p_http_error_fails_action(
    _mock_utils_1p: MagicMock,
    _mock_factory_1p: MagicMock,
    status_code: int,
    error_body: str,
    action_output: MockActionOutput,
) -> None:
    """Verify 1P 403/404/500 responses fail GetSiemplifyUsers and surface the API error body."""
    err_resp = requests.Response()
    err_resp.status_code = status_code
    err_resp.reason = "API Error"
    err_resp.url = "https://soar.example.com/v1alpha/projects/p/locations/us/instances/i/legacySoarUsers"
    err_resp._content = error_body.encode()

    with patch(
        "TIPCommon.rest.soar_platform_clients.base_soar_api.BaseSoarApi._make_request",
        return_value=err_resp,
    ):
        GetSiemplifyUsers.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert "Returned Siemplify Users." not in action_output.results.output_message
    assert "Error executing action 'GetSiemplifyUsers'." in action_output.results.output_message
    assert str(status_code) in action_output.results.output_message
    assert error_body in action_output.results.output_message
    assert action_output.results.json_output is None
