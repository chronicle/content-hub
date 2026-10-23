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

from TIPCommon.base.action import ExecutionState

from ...actions import execute_http_request
from .. import common
from ..core.session import AzureApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_MESSAGE: str = "Successfully executed API request."


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Method": "GET",
        "URL Path": ("https://graph.microsoft.com/v1.0/xyz-xyz/users"),
        "URL Params": '{"$top": "2"}',
        "Headers": '{"Accept": "application/json"}',
        "Follow Redirects": True,
        "Fail on 4xx/5xx": False,
        "Password Protect Zip": False,
        "Request Timeout": 30,
        "Fields To Return": "response_data",
    },
)
def test_execute_get_request_success(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    execute_http_request.main()
    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "response_data" in action_output.results.json_output.json_result


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Method": "POST",
        "URL Path": "https://graph.microsoft.com/v1.0/xyz-xyz/users",
        "Body Payload": '{"displayName": "test"}',
        "Fields To Return": "response_data",
        "Request Timeout": 30,
    },
)
def test_execute_post_request_success(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    execute_http_request.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "response_data" in action_output.results.json_output.json_result


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Method": "GET",
        "URL Path": "https://graph.microsoft.com/v1.0/xyz-xyz/users",
        "URL Params": '{"$top": "2"}',
        "Headers": '{"Accept": "invalid/header"}',
        "Fields To Return": "response_data",
        "Request Timeout": 30,
        "Fail on 4xx/5xx": True,
    },
)
def test_execute_request_failed(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    execute_http_request.main()

    assert len(script_session.request_history) == 2
    assert not action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.FAILED
