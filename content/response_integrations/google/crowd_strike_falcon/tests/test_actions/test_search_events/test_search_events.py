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

import datetime

from crowd_strike_falcon.actions import SearchEvents
from crowd_strike_falcon.tests.common import CONFIG_PATH
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState
from TIPCommon.types import SingleJson

SUCCESS_OUTPUT_MESSAGE_NO_RESULTS: str = (
    'No results were found for the query "no_data_query_test" in CrowdStrikeFalcon.'
)
SUCCESS_OUTPUT_MESSAGE_RESULTS: str = (
    'Successfully returned results for the query "data_query_test" in '
    "CrowdStrikeFalcon."
)
MAX_RESULTS_OUTPUT_MESSAGE: str = (
    'Failed to execute action. Error: Invalid parameter "Max Results To Return". '
    "The value must be between 1 and 1000. Wrong value provided: 1001"
)
MIN_RESULTS_OUTPUT_MESSAGE: str = (
    'Failed to execute action. Error: Invalid parameter "Max Results To Return". '
    "The value must be between 1 and 1000. Wrong value provided: -1"
)
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10,
)
TIMEOUT_NO_RESULTS: SingleJson = {
    "execution_deadline_unix_time_ms": int(SCRIPT_DEADLINE_TIME.timestamp() * 1000),
}
TIMEOUT_RESULTS: SingleJson = {
    "execution_deadline_unix_time_ms": int(SCRIPT_DEADLINE_TIME.timestamp() * 1000),
}
TIMEOUT_MAX_RESULTS_TO_PARAM: SingleJson = {
    "execution_deadline_unix_time_ms": int(SCRIPT_DEADLINE_TIME.timestamp() * 1000),
}
TIMEOUT_MIN_RESULTS_TO_PARAM: SingleJson = {
    "execution_deadline_unix_time_ms": int(SCRIPT_DEADLINE_TIME.timestamp() * 1000),
}


@set_metadata(
    parameters={
        "Repository": "Falcon",
        "Query": "no_data_query_test",
        "Time Frame": "Last Hour",
        "Max Results To Return": 1,
    },
    integration_config_file_path=CONFIG_PATH,
    input_context=TIMEOUT_NO_RESULTS,
)
def test_search_events_action_success_no_results(
    script_session: CrowdStrikeFalconSession,
    action_output: MockActionOutput,
) -> None:

    SearchEvents.main()

    assert len(script_session.request_history) == 3
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE_NO_RESULTS
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Repository": "All",
        "Query": "data_query_test",
        "Time Frame": "Last Hour",
        "Max Results To Return": 1,
    },
    integration_config_file_path=CONFIG_PATH,
    input_context=TIMEOUT_RESULTS,
)
def test_search_events_action_success_results(
    script_session: CrowdStrikeFalconSession,
    action_output: MockActionOutput,
) -> None:

    SearchEvents.main()

    assert len(script_session.request_history) == 3
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE_RESULTS
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Repository": "All",
        "Query": "data_query_test",
        "Time Frame": "Last Hour",
        "Max Results To Return": 1001,
    },
    integration_config_file_path=CONFIG_PATH,
    input_context=TIMEOUT_MAX_RESULTS_TO_PARAM,
)
def test_search_events_action_validate_max_results_param(
    script_session: CrowdStrikeFalconSession,
    action_output: MockActionOutput,
) -> None:

    SearchEvents.main()

    assert len(script_session.request_history) == 0
    assert action_output.results.output_message == MAX_RESULTS_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters={
        "Repository": "All",
        "Query": "data_query_test",
        "Time Frame": "Last Hour",
        "Max Results To Return": -1,
    },
    integration_config_file_path=CONFIG_PATH,
    input_context=TIMEOUT_MIN_RESULTS_TO_PARAM,
)
def test_search_events_action_validate_min_results_param(
    script_session: CrowdStrikeFalconSession,
    action_output: MockActionOutput,
) -> None:

    SearchEvents.main()

    assert len(script_session.request_history) == 0
    assert action_output.results.output_message == MIN_RESULTS_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
