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

from urllib.parse import urlencode

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ...actions import generate_token
from .. import common
from ..core.session import AzureApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


TOKEN_GENERATED_MESSAGE: str = "Successfully fetched the refresh token: \n{}\n"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={
        "Authorization URL": (f"http://localhost?{urlencode({'code': 'valid_code'})}"),
    },
)
def test_generate_token_success(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    generate_token.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=TOKEN_GENERATED_MESSAGE.format("new_refresh_token"),
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Authorization URL": "http://localhost?code=invalid_code"},
)
def test_generate_token_invalid_code(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    generate_token.main()

    assert len(script_session.request_history) == 1
    assert not action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Authorization URL": "http://localhost"},
)
def test_generate_token_missing_code(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    generate_token.main()

    assert len(script_session.request_history) == 0
    assert not action_output.results.result_value
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert "The 'code' parameter is missing" in action_output.results.output_message
