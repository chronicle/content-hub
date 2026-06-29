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
import pathlib
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from google_sec_ops_ai_agents.actions import ping
from google_sec_ops_ai_agents.tests import common
from google_sec_ops_ai_agents.tests.core.product import GoogleSecOpsAiAgents
from google_sec_ops_ai_agents.tests.core.session import GoogleSecOpsAiAgentsSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    google_chronicle_ai_agents.cleanup_investigations()
    google_chronicle_ai_agents.add_investigations("siemplify-connectivity-test", [{"name": "test"}])
    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=ping.SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
