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

from ...actions import get_authorization
from .. import common
from ..core.session import AzureApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


AUTH_URL_GENERATED_MESSAGE: str = "Authorization URL generated successfully."
BROWSE_AUTH_LINK_MESSAGE: str = "Browse to this authorization link"


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Oauth Scopes": "user.read, offline_access"},
)
def test_get_authorization_success(
    script_session: AzureApiSession,
    action_output: MockActionOutput,
) -> None:
    get_authorization.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == ActionOutput(
        output_message=AUTH_URL_GENERATED_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
