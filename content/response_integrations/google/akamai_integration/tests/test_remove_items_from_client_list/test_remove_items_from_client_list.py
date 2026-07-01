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

from ...actions.remove_items_from_client_list import (
    RemoveItemsFromClientList,
)
from ...core.datamodels import ClientList, ClientListItem
from ...tests import common
from ...tests.core.session import AkamaiSession
from ...tests.core.product import Akamai
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "Successfully updated client list in Akamai."
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action \"Akamai - Remove Items From Client Lists\".\nReason:"
    " \"Test_Fail\" client list wasn\'t found in Akamai."
)


@set_metadata(
    parameters={
        "Client List Name": "Test_Success",
        "Item Value": "11.11.11.11, 12.12.12.12",
    },
    integration_config_file_path=common.CONFIG_PATH,
)
def test_remove_items_from_client_list_success(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    client_list_1: ClientList = copy.deepcopy(common.CLIENT_LIST)
    client_list_1.raw_data["name"] = "Test_Success"
    client_list_1.raw_data["items"][0]["value"] = "11.11.11.11"
    client_list_1.raw_data["items"][1]["value"] = "12.12.12.12"

    client_list_item_1: ClientListItem = copy.deepcopy(common.REMOVE_CLIENT_LIST_ITEM)
    client_list_item_2: ClientListItem = copy.deepcopy(common.REMOVE_CLIENT_LIST_ITEM)

    client_list_item_1.raw_data["value"] = "11.11.11.11"
    client_list_item_2.raw_data["value"] = "12.12.12.12"

    akamai.add_client_lists(client_list_1)
    akamai.add_client_list_items(client_list_item_1)
    akamai.add_client_list_items(client_list_item_2)

    RemoveItemsFromClientList().run()

    assert len(script_session.request_history) == 3
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Client List Name": "Test_Fail",
        "Item Value": "11.11.11.11, 12.12.12.12",
    },
    integration_config_file_path=common.CONFIG_PATH,
)
def test_remove_items_from_client_list_failed(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    client_list_1: ClientList = copy.deepcopy(common.CLIENT_LIST)
    client_list_1.raw_data["name"] = "AJBLJBJB"

    client_list_item_1: ClientListItem = copy.deepcopy(common.REMOVE_CLIENT_LIST_ITEM)
    client_list_item_2: ClientListItem = copy.deepcopy(common.REMOVE_CLIENT_LIST_ITEM)

    client_list_item_1.raw_data["value"] = "11.11.11.11"
    client_list_item_2.raw_data["value"] = "12.12.12.12"

    akamai.add_client_lists(client_list_1)
    akamai.add_client_list_items(client_list_item_1)
    akamai.add_client_list_items(client_list_item_2)

    RemoveItemsFromClientList().run()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
