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

from azure_monitor.actions import ping
from azure_monitor.tests import common
from azure_monitor.tests.core.product import AzureMonitor
from azure_monitor.tests.core.session import AzureMonitorSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Azure Monitor server with the provided connection "
    "parameters!"
)

FAILED_OUTPUT_MESSAGE: str = (
    "Failed to connect to the Azure Monitor server!\nReason: "
    "Please Check your Credentials."
)


# pylint: disable=unused-argument


@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    ping.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


FAILED_CONFIG = common.CONFIG.copy()
FAILED_CONFIG["Client ID"] = "invalid_client_id"


@set_metadata(integration_config=FAILED_CONFIG)
def test_ping_failed(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
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
