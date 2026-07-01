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

import pathlib
from ...actions import SearchEvents
from ...tests import common
from ...tests.core.product import ProofPointTAP
from ...tests.core.session import ProofPointTAPSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = "Successfully returned events from Proofpoint TAP."

NO_EVENTS_FOUND_MESSAGE: str = (
    "No events were found in Proofpoint TAP for the provided criteria."
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Event Type": "All",
    "Threat Status": "Active",
    "Time Frame": "Last Hour",
    "Start Time": "",
    "End Time": "",
    "Max Results To Return": 1,
}
SUCCESS_PARAMETERS: dict[str, str] = {
    "Event Type": "All",
    "Threat Status": "Cleared",
    "Time Frame": "Last Hour",
    "Start Time": "",
    "End Time": "",
    "Max Results To Return": 1,
}


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_search_events_action_no_events_success(
    proof_point_tap: ProofPointTAP,
    script_session: ProofPointTAPSession,
    action_output: MockActionOutput,
) -> None:
    proof_point_tap.add_event(common.SEARCH_EVENTS_NO_DATA)
    SearchEvents.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == NO_EVENTS_FOUND_MESSAGE
    assert action_output.results.result_value is True


@set_metadata(integration_config=common.CONFIG, parameters=SUCCESS_PARAMETERS)
def test_search_events_action_with_events_success(
    proof_point_tap: ProofPointTAP,
    script_session: ProofPointTAPSession,
    action_output: MockActionOutput,
) -> None:
    proof_point_tap.add_event(common.SEARCH_EVENTS)
    SearchEvents.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
