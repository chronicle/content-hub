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

from ...actions import UpdateNotableEvents
from ...actions.UpdateNotableEvents import STATUS_MAPPER
from ...core.constants import DISPOSITION_MAPPER
from ...core.datamodels import NotableEvent
from ...tests.common import create_notable_event
from ...tests.const import CONFIG_PATH
from ...tests.core.product import Splunk
from ...tests.core.session import SplunkSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ENDPOINT: str = "/services/notable_update"
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully updated {number_of_ids} notable events in Splunk."
)
FAILURE_OUTPUT_MESSAGE: str = (
    "Action wasn't able to update notable events. "
    "Reason:{{'message': [{{'text': 'Mock Message: event {event_id} not found'}}]}}"
)

EVENT_IDS: list[str] = ["1", "2", "3"]
NEW_URGENCY: str = "very very urgent"
NEW_OWNER: str = "åß∂øœµ∑ßחחחח"
NEW_DISPOSITION: str = "Undefined"
NEW_COMMENT: str = "GG EZ LOL"
NEW_STATUS: str = "Unassigned"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Notable Event IDs": ",".join(EVENT_IDS),
        "Urgency": NEW_URGENCY,
        "Status": NEW_STATUS,
        "Comment": NEW_COMMENT,
        "New Owner": NEW_OWNER,
        "Disposition": NEW_DISPOSITION,
    },
)
def test_with_all_parameters_with_unicode_succeeds(
    splunk: Splunk,
    script_session: SplunkSession,
    action_output: MockActionOutput,
) -> None:
    events: list[NotableEvent] = [create_notable_event(id_) for id_ in EVENT_IDS]
    splunk.add_notable_events(events)

    for event in splunk.get_notable_events(EVENT_IDS):
        assert event.urgency != NEW_URGENCY
        assert event.status != STATUS_MAPPER[NEW_STATUS]
        assert not event.comments
        assert event.raw_data["owner"] != NEW_OWNER
        assert (
            event.raw_data["disposition"]
            != f"disposition:{DISPOSITION_MAPPER[NEW_DISPOSITION]}"
        )


    UpdateNotableEvents.main()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[-1].request.real_url == ENDPOINT
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_OUTPUT_MESSAGE.format(number_of_ids=len(EVENT_IDS)),
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )

    for event in splunk.get_notable_events(EVENT_IDS):
        assert event.urgency == NEW_URGENCY
        assert event.status == STATUS_MAPPER[NEW_STATUS]
        assert NEW_COMMENT in event.comments
        assert event.raw_data["owner"] == NEW_OWNER
        assert (
            event.raw_data["disposition"]
            == f"disposition:{DISPOSITION_MAPPER[NEW_DISPOSITION]}"
        )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Notable Event IDs": EVENT_IDS[0],
        "Urgency": NEW_URGENCY,
        "Status": NEW_STATUS,
        "Comment": NEW_COMMENT,
        "New Owner": NEW_OWNER,
        "Disposition": NEW_DISPOSITION,
    },
)
def test_with_invalid_event_id_fails(
    splunk: Splunk,
    script_session: SplunkSession,
    action_output: MockActionOutput,
) -> None:
    event_id: str = "0"
    assert event_id not in EVENT_IDS
    new_event: NotableEvent = create_notable_event(event_id=event_id)
    splunk.add_notable_event(new_event)

    UpdateNotableEvents.main()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[-1].request.real_url == ENDPOINT
    assert action_output.results == ActionOutput(
        output_message=FAILURE_OUTPUT_MESSAGE.format(event_id=EVENT_IDS[0]),
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
