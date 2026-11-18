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

from google_threat_intelligence.actions import ping
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Google Threat Intelligence "
    "server with the provided connection parameters!"
)


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:

    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )
