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
import datetime

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import SingleJson

from microsoft_defender_atp.actions import (
    GetMachineRecommendations,
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

SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)

HOSTNAME_ENTITY: EntityTypesEnum = create_entity(
    identifier=common.MOCK_DATA["machine_data"]["computerDnsName"],
    type_=EntityTypesEnum.HOST_NAME,
)
IP_ENTITY: EntityTypesEnum = create_entity(
    identifier=common.MOCK_DATA["machine_data_ip"]["lastIpAddress"],
    type_=EntityTypesEnum.ADDRESS,
)

DEFAULT_PARAMS: SingleJson = {
    "Max Recommendations To Return": 50,
}

HOSTNAME: str = common.MOCK_DATA["machine_data"]["computerDnsName"]
IP_ADDRESS: str = common.MOCK_DATA["machine_data_ip"]["lastIpAddress"]

NOT_FOUND_ENTITY_IDENTIFIER: str = "not.found.com"
NOT_FOUND_ENTITY: EntityTypesEnum = create_entity(
    identifier=NOT_FOUND_ENTITY_IDENTIFIER, type_=EntityTypesEnum.HOST_NAME
)
INTEGRATION_IDENTIFIER: str = "Microsoft Defender for Endpoint"
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully returned recommendations for the following endpoints in "
    f"{INTEGRATION_IDENTIFIER}:"
)
NOT_FOUND_OUTPUT_MESSAGE: str = (
    "No recommendations were found for the provided endpoints in "
    f"{INTEGRATION_IDENTIFIER}."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_machine_recommendations_success(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for successful execution of the GetMachineRecommendations action."""
    machine_data: dict = copy.deepcopy(common.MOCK_DATA["machine_data"])
    machine_data_ip: dict = copy.deepcopy(common.MOCK_DATA["machine_data_ip"])
    microsoft_defender_atp.add_machine(machine_data)
    microsoft_defender_atp.add_machine(machine_data_ip)
    recommendation_data: dict = copy.deepcopy(common.MOCK_DATA["recommendation_data"])
    recommendation_data["machineId"] = machine_data["id"]
    microsoft_defender_atp.add_recommendation(recommendation_data)

    recommendation_data_ip: dict = copy.deepcopy(
        common.MOCK_DATA["recommendation_data"]
    )
    recommendation_data_ip["id"] = "va-win-10263"
    recommendation_data_ip["machineId"] = machine_data_ip["id"]
    microsoft_defender_atp.add_recommendation(recommendation_data_ip)

    GetMachineRecommendations.main()

    assert len(script_session.request_history) == 5
    assert SUCCESS_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert len(action_output.results.json_output.json_result) == 2


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
)
def test_get_machine_recommendations_not_found(
    microsoft_defender_atp: MicrosoftDefenderATP,
    script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test for GetMachineRecommendations action when an endpoint is not found."""
    microsoft_defender_atp.cleanup_machines()

    GetMachineRecommendations.main()

    assert len(script_session.request_history) == 2
    assert NOT_FOUND_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value in (True, "true")
    assert action_output.results.execution_state == ExecutionState.COMPLETED
