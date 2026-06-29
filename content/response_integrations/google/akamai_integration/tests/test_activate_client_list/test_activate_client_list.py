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

from akamai_integration.actions.activate_client_list import ActivateClientList
from akamai_integration.core.datamodels import ClientList, ClientActivation
from akamai_integration.tests.common import (
    ACTIVATE_CLIENT_LIST,
    CLIENT_LIST,
    CONFIG_PATH,
)
from akamai_integration.tests.core.product import Akamai
from akamai_integration.tests.core.session import AkamaiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "Successfully activated the client list in Akamai."
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action \"Akamai - Activate Client List\"\nReason: 'Testing_Geo1' "
    "client list wasn't found in Akamai."
)


@set_metadata(
    parameters={
        "Client List Name": "Testing_Geo",
        "Environment": "Production",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_activate_client_list_success(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    client_list_1: ClientList = copy.deepcopy(CLIENT_LIST)
    client_list_2: ClientList = copy.deepcopy(CLIENT_LIST)

    client_list_1.name = "Testing_Geo"
    client_list_1.list_id = "238746_TESTINGGEO"

    client_list_2.name = "AJBLJBJB"
    client_list_2.list_id = "238789_TESTINGIP"

    akamai.add_client_lists(client_list_1)
    akamai.add_client_lists(client_list_2)

    client_activation: ClientActivation = copy.deepcopy(ACTIVATE_CLIENT_LIST)
    akamai.add_client_activation(client_activation)

    ActivateClientList().run()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED

@set_metadata(
    parameters={
        "Client List Name": "Testing_Geo1",
        "Environment": "Production",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_activate_client_list_failed(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    akamai.add_client_lists(CLIENT_LIST)
    akamai.add_client_activation(ACTIVATE_CLIENT_LIST)

    ActivateClientList().run()

    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
