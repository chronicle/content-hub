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
from TIPCommon.base.data_models import ActionOutput

from ...actions import ping
from .. import common
from ..core.session import AzureApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


PING_SUCCESS_MESSAGE: str = "Successfully connected to the Azure API."

FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "AzureApi - Ping"\n'
    "Reason: An error occurred: unauthorized_client"
)


@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    ping.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == PING_SUCCESS_MESSAGE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert "endpoint" in action_output.results.json_output.json_result


FAILED_CONFIG: dict[str, str] = common.CONFIG.copy()
FAILED_CONFIG["Client ID"] = "invalid_client_id"


@set_metadata(integration_config=FAILED_CONFIG)
def test_ping_failed(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
