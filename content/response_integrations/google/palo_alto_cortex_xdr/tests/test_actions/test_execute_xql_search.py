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

import copy
import datetime
from TIPCommon.base.action import ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from ...actions import ExecuteXQLSearch
from ...core.constants import (
    EXECUTE_XQL_SEARCH_ACTION_SCRIPT_NAME,
    PRODUCT,
    VENDOR,
)
from ...tests import common
from ...tests.core.session import PaloAltoCortexXDRSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


QUERY: str = "dataset=xdr_data"
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully returned results for the query \"{QUERY}\" in {VENDOR} {PRODUCT}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{EXECUTE_XQL_SEARCH_ACTION_SCRIPT_NAME}".\nReason: '
    "An error occurred: An error occurred while processing XDR public API - "
    "incident management - get_incident_extra_data - Incident not found"
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Query": QUERY,
    "Time Frame": "Last Hour",
    "Max Results To Return": "50",
}
FAILED_PARAMETERS: dict[str, str] = copy.deepcopy(DEFAULT_PARAMETERS)
FAILED_PARAMETERS["Incident ID"] = common.INVALID_INCIDENT_ID
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_execute_xql_search_action_success(
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:

    ExecuteXQLSearch.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result is not None
