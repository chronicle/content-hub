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
from ...actions import ping

from ...tests import common
from ...tests.core.product import (
    ProofpointCloudThreatResponse,
)
from ...tests.core.session import (
    ProofpointCloudThreatResponseSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Proofpoint Cloud Threat Response server "
    "with the provided connection parameters!"
)
PING_FAIL_MESSAGE: str = (
    "Failed to connect to the Proofpoint Cloud Threat Response server!\n"
    'Reason: 400: {"error": {"message": "Failed to authenticate to '
    'Proofpoint Cloud Threat Response", "errors": [{"errorMessage": "Wrong '
    'Credentials!"}]}}'
)


@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    proofpoint_ctr: ProofpointCloudThreatResponse,
    script_session: ProofpointCloudThreatResponseSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful ping action"""
    proofpoint_ctr.cleanup_incidents()
    proofpoint_ctr.add_incidents("", common.INCIDENTS_JSON)
    ping.main()
    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


FAILED_CONFIG = common.CONFIG.copy()
FAILED_CONFIG["Client Secret"] = "invalid client secret"


@set_metadata(integration_config=FAILED_CONFIG)
def test_ping_fail(
    script_session: ProofpointCloudThreatResponseSession,
    action_output: MockActionOutput,
) -> None:
    """Test for failed ping action"""
    ping.main()
    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=PING_FAIL_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
