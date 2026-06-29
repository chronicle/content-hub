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
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from akamai_integration.actions.remove_items_from_network_list import (
    RemoveItemsFromNetworkLists,
)
from akamai_integration.tests.common import (
    CONFIG_PATH,
    NETWORK_ITEM_LIST,
    NETWORK_LIST,
)
from akamai_integration.tests.core.session import AkamaiSession
from akamai_integration.tests.core.product import Akamai
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "Successfully updated network list in Akamai."
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "Akamai - Remove Items From Network List"\nReason: "Test!" '
    "network list wasn't found in Akamai."
)


@set_metadata(
    parameters={
        "Network List Name": "Test",
        "Items": "127.0.0.24",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_remove_items_from_network_list_success(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    akamai.add_network_lists(NETWORK_LIST)
    akamai.add_network_item_list(NETWORK_ITEM_LIST)

    RemoveItemsFromNetworkLists().run()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Network List Name": "Test!",
        "Items": "127.0.0.24",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_remove_items_from_network_list_failed(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    akamai.add_network_lists(NETWORK_LIST)
    akamai.add_network_item_list(NETWORK_ITEM_LIST)

    RemoveItemsFromNetworkLists().run()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
