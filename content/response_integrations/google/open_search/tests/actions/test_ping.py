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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from open_search.actions import ping
from open_search.tests.common import CONFIG_PATH
from open_search.tests.core.session import OpenSearchSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_OUTPUT = ActionOutput(
    output_message="Successfully connected to the OpenSearch server.",
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)

# This output reflects a 401 Unauthorized error, which is a type of connection failure.
PING_FAILED_OUTPUT = ActionOutput(
    output_message=(
        "Failed to connect OpenSearch server\n"
        "Reason: AuthenticationException(401, 'Unauthorized')"
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping_success(
    os_mock_session: OpenSearchSession,
    action_output: MockActionOutput,
) -> None:
    ping.main()
    assert len(os_mock_session.request_history) == 1
    assert action_output.results == PING_SUCCESS_OUTPUT
