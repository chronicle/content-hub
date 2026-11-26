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
import json

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity

from g_suite.actions import SearchUserActivityEvents
from g_suite.tests.common import CONFIG, SEARCH_USER_ACTIVITY_EVENTS_MOCK
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully found events for the following users in Google Workspace: "
    "mockuser1@example.com."
)
FAILED_OUTPUT_MESSAGE: str = (
    "No events were found for the following users in Google Workspace: "
    "mockuser1@example.com."
)

USER_ENTITY_1_STR: str = "mockuser1@example.com"
USER_ENTITY_1_OBJ: Entity = create_entity(USER_ENTITY_1_STR, EntityTypesEnum.USER)
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)
ACTION_PARAMETERS: dict[str, str | int] = {
    "Application Names": json.dumps(["Token"]),
    "Time Frame": "Last Month",
    "Max Events To Return": 200,
}
FAILED_ACTION_PARAMETERS: dict[str, str | int] = {
    "Application Names": json.dumps(["Login"]),
    "Time Frame": "Last Month",
    "Max Events To Return": 200,
}


@set_metadata(
    integration_config=CONFIG,
    parameters=ACTION_PARAMETERS,
    entities=[USER_ENTITY_1_OBJ],
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_search_user_activity_events_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_user_activity_events(SEARCH_USER_ACTIVITY_EVENTS_MOCK)

    SearchUserActivityEvents.main()
    assert len(script_session.request_history) >= 3
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=CONFIG,
    parameters=FAILED_ACTION_PARAMETERS,
    entities=[USER_ENTITY_1_OBJ],
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_search_user_activity_events_failed(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_user_activity_events(SEARCH_USER_ACTIVITY_EVENTS_MOCK)

    SearchUserActivityEvents.main()
    assert len(script_session.request_history) >= 3
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED
