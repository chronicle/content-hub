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

import copy

from TIPCommon.base.action import ExecutionState, EntityTypesEnum
from TIPCommon.types import SingleJson

from microsoft_defender_atp.actions import (
    GetUserRelatedAlerts,
)

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import (
    MicrosoftDefenderATP,
)
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


USER_ENTITY: EntityTypesEnum = create_entity(
    identifier=common.MOCK_DATA["user_related_alert"]["actor"]["accountId"],
    type_=EntityTypesEnum.USER,
)

NOT_FOUND_USER_ENTITY: EntityTypesEnum = create_entity(
    identifier="notfound@test.com",
    type_=EntityTypesEnum.USER,
)

DEFAULT_PARAMS: SingleJson = {
    "Max Alerts To Return": 100,
}

SUCCESS_MESSAGE: str = (
    "Successfully returned alerts related to the following users in "
    "Microsoft Defender for Endpoint: test@test.com."
)
NOT_FOUND_MESSAGE: str = (
    "No alerts were related to the provided users in Microsoft Defender for Endpoint."
)
FAILED_MESSAGE: str = "No alerts were related to the provided users"
INVALID_PARAM_MESSAGE: str = (
    "Invalid value provided for 'Max Alerts To Return' parameter"
)
NO_SUITABLE_ENTITIES_MESSAGE: str = "No suitable entities found"


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[USER_ENTITY],
    input_context={},
)
def test_get_user_related_alerts_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful execution of the GetUserRelatedAlerts action."""
    microsoft_defender_atp.add_user_related_alert(
        common.MOCK_DATA["success_alert_data"]
    )

    GetUserRelatedAlerts.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output_message = action_output.results.output_message
    assert SUCCESS_MESSAGE in output_message
    json_results = action_output.results.json_output.json_result
    assert any(USER_ENTITY.identifier == res["Entity"].upper() for res in json_results)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_USER_ENTITY],
    input_context={},
)
def test_get_user_related_alerts_not_found(
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for GetUserRelatedAlerts action when no alerts are found."""
    GetUserRelatedAlerts.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output_message = action_output.results.output_message
    assert NOT_FOUND_MESSAGE in output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[USER_ENTITY],
    input_context={},
)
def test_get_user_related_alerts_failed(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for GetUserRelatedAlerts action when the API call fails."""
    microsoft_defender_atp.add_user_related_alert(
        copy.deepcopy(common.MOCK_DATA["user_related_alert"]), fail_request=True
    )

    GetUserRelatedAlerts.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output_message = action_output.results.output_message
    assert NOT_FOUND_MESSAGE in output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters={"Max Alerts To Return": 0},
    entities=[USER_ENTITY],
    input_context={},
)

@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[],
    input_context={},
)
def test_get_user_related_alerts_no_suitable_entities(
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for GetUserRelatedAlerts action when no suitable entities are provided."""
    GetUserRelatedAlerts.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (False, "false")
    output_message = action_output.results.output_message
    assert NO_SUITABLE_ENTITIES_MESSAGE in output_message
