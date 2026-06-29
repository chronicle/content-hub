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
import copy

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from akamai_integration.actions.get_client_lists import GetClientLists
from akamai_integration.core.datamodels import ClientList
from akamai_integration.tests import common
from akamai_integration.tests.core.session import AkamaiSession
from akamai_integration.tests.core.product import Akamai
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "Successfully returned client lists from Akamai."
FAILED_OUTPUT_MESSAGE: str = (
    "No clients lists were found for the provided criteria in Akamai."
)


@set_metadata(
    parameters={
        "Client List Name": "Testing_Ip",
        "Type": "IP",
        "Max Client Lists To Return": 10,
        "Max Client List Items To Return": 10,
    },
    integration_config_file_path=common.CONFIG_PATH,
)
def test_get_client_lists_success(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    client_list_1: ClientList = copy.deepcopy(common.CLIENT_LIST)
    client_list_2: ClientList = copy.deepcopy(common.CLIENT_LIST)

    client_list_1.raw_data["name"] = "Testing_Geo"
    client_list_1.raw_data["listId"] = "238746_TESTINGGEO"
    client_list_1.raw_data["type"] = "GEO"
    client_list_1.raw_data["items"][0]["value"] = "CH"
    client_list_1.raw_data["items"][1]["value"] = "CN"

    client_list_2.raw_data["name"] = "Testing_Ip"
    client_list_2.raw_data["listId"] = "238789_TESTINGIP"
    client_list_2.raw_data["type"] = "IP"
    client_list_2.raw_data["items"][0]["value"] = "1.1.1.1"
    client_list_2.raw_data["items"][1]["value"] = "2.2.2.2"

    akamai.add_client_lists(client_list_1)
    akamai.add_client_lists(client_list_2)

    GetClientLists().run()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Client List Name": "Test_Fail",
        "Type": "IP",
        "Max Client Lists To Return": 10,
        "Max Client List Items To Return": 10,
    },
    integration_config_file_path=common.CONFIG_PATH,
)
def test_get_client_lists_failed(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    client_list_1: ClientList = copy.deepcopy(common.CLIENT_LIST)
    client_list_2: ClientList = copy.deepcopy(common.CLIENT_LIST)

    client_list_1.raw_data["name"] = "Testing_Geo"
    client_list_1.raw_data["listId"] = "238746_TESTINGGEO"
    client_list_1.raw_data["type"] = "GEO"
    client_list_1.raw_data["items"][0]["value"] = "CH"
    client_list_1.raw_data["items"][1]["value"] = "CN"

    client_list_2.raw_data["name"] = "Testing_Ip"
    client_list_2.raw_data["listId"] = "238789_TESTINGIP"
    client_list_2.raw_data["type"] = "IP"
    client_list_2.raw_data["items"][0]["value"] = "1.1.1.1"
    client_list_2.raw_data["items"][1]["value"] = "2.2.2.2"

    akamai.add_client_lists(client_list_1)
    akamai.add_client_lists(client_list_2)

    GetClientLists().run()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
