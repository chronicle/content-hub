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

from azure_monitor.actions import search_logs
from azure_monitor.tests import common
from azure_monitor.tests.core.product import AzureMonitor
from azure_monitor.tests.core.session import AzureMonitorSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_MESSAGE: str = (
    'Successfully returned results for the query "{query}" in Azure Monitor.'
)
NO_RESULTS_OUTPUT_MESSAGE: str = (
    'No results were found for the query "invalid_query" in Azure Monitor.'
)

CUSTOM_TIME_FRAME_VALIDATION_MESSAGE: str = (
    'Error executing action "AzureMonitor - Search Logs"\n'
    "Reason: 'Start Time' must be provided if 'Time Frame' is set to 'Custom'."
)
ISO_FORMAT_VALIDATION_MESSAGE: str = (
    'Error executing action "AzureMonitor - Search Logs"\n'
    "Reason: 'Start Time' must be a valid ISO 8601 datetime string "
    "(e.g., '2025-10-29T10:15:00Z'). Provided: 'abc'"
)
MAX_RESULTS_MIN_LIMIT_MESSAGE: str = (
    'Error executing action "AzureMonitor - Search Logs"\n'
    'Reason: Invalid parameter "Max Results To Return". The value must be between 1 '
    "and 1000. Wrong value provided: -1"
)
MAX_RESULTS_MAX_LIMIT_MESSAGE: str = (
    'Error executing action "AzureMonitor - Search Logs"\n'
    'Reason: Invalid parameter "Max Results To Return". The value must be between 1 '
    "and 1000. Wrong value provided: 1001"
)
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "AzureMonitor - Search Logs"\n'
    "Reason: Invalid Workspace ID."
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Last Hour",
    "Max Results To Return": 100,
}
PARAMETERS_INVALID_QUERY: dict[str, str] = {
    "Query": "invalid_query",
    "Time Frame": "Last Hour",
    "Max Results To Return": 100,
}
CUSTOM_TIME_FRAME_VALIDATION_PARAMETERS: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Custom",
    "Max Results To Return": 100,
}
CUSTOM_TIME_FRAME_SUCCESSFUL_EXECUTION_PARAMETERS: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Custom",
    "Max Results To Return": 100,
    "Start Time": "2025-10-29T10:15:00Z",
    "End Time": "2025-10-29T12:15:00Z",
}
ISO_FORMAT_VALIDATION_PARAMETERS: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Custom",
    "Max Results To Return": 100,
    "Start Time": "abc",
    "End Time": "xyz",
}
MAX_RESULTS_MIN_LIMIT_PARAMETERS_VALIDATION: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Last Hour",
    "Max Results To Return": -1,
}
MAX_RESULTS_MAX_LIMIT_PARAMETERS_VALIDATION: dict[str, str] = {
    "Query": "AzureActivity",
    "Time Frame": "Last Hour",
    "Max Results To Return": 1001,
}
WORKSPACE_ID_PARAMETERS: dict[str, str] = {
    "Workspace ID": "workspace_id",
    "Query": "AzureActivity",
    "Time Frame": "Last Hour",
    "Max Results To Return": 100,
}
INVALID_WORKSPACE_ID_PARAMETERS: dict[str, str] = {
    "Workspace ID": "invalid_workspace_id",
    "Query": "AzureActivity",
    "Time Frame": "Last Hour",
    "Max Results To Return": 100,
}

JSON_OUTPUT_RESULT: list[dict[str, str]] = [
    {
        "TimeGenerated": "2025-10-29T12:42:44.6629245Z",
        "OperationName": "Create role assignment",
    },
    {
        "TimeGenerated": "2025-10-29T12:42:44.6782565Z",
        "OperationName": "Create role assignment",
    },
]


# pylint: disable=unused-argument


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_search_logs_success(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    search_logs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE.format(query=query)
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result == JSON_OUTPUT_RESULT


@set_metadata(integration_config=common.CONFIG, parameters=PARAMETERS_INVALID_QUERY)
def test_search_logs_invalid_query(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    search_logs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == NO_RESULTS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is None


@set_metadata(
    integration_config=common.CONFIG,
    parameters=CUSTOM_TIME_FRAME_VALIDATION_PARAMETERS,
)
def test_search_logs_custom_time_frame_validation(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    search_logs.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == CUSTOM_TIME_FRAME_VALIDATION_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None


@set_metadata(
    integration_config=common.CONFIG,
    parameters=ISO_FORMAT_VALIDATION_PARAMETERS,
)
def test_search_logs_iso_format_validation(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    search_logs.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == ISO_FORMAT_VALIDATION_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None


@set_metadata(
    integration_config=common.CONFIG,
    parameters=CUSTOM_TIME_FRAME_SUCCESSFUL_EXECUTION_PARAMETERS,
)
def test_search_logs_success_with_custom_time_frame(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    search_logs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE.format(query=query)
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result == JSON_OUTPUT_RESULT


@set_metadata(
    integration_config=common.CONFIG,
    parameters=MAX_RESULTS_MIN_LIMIT_PARAMETERS_VALIDATION,
)
def test_search_logs_max_results_min_limit_validation(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    search_logs.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == MAX_RESULTS_MIN_LIMIT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None


@set_metadata(
    integration_config=common.CONFIG,
    parameters=MAX_RESULTS_MAX_LIMIT_PARAMETERS_VALIDATION,
)
def test_search_logs_max_results_max_limit_validation(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    search_logs.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == MAX_RESULTS_MAX_LIMIT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None


@set_metadata(integration_config=common.CONFIG, parameters=WORKSPACE_ID_PARAMETERS)
def test_search_logs_success_with_workspace_id(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    search_logs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_MESSAGE.format(query=query)
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result == JSON_OUTPUT_RESULT


@set_metadata(
    integration_config=common.CONFIG,
    parameters=INVALID_WORKSPACE_ID_PARAMETERS,
)
def test_search_logs_failed_with_invalid_workspace_id(
    azure_monitor: AzureMonitor,
    script_session: AzureMonitorSession,
    action_output: MockActionOutput,
) -> None:
    azure_monitor.cleanup_logs()
    query = "AzureActivity"
    azure_monitor.add_logs(query, common.LIST_LOG_ENTRY)
    search_logs.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None
