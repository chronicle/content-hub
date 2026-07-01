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

from ...actions import ping
from ...tests.common import (
    CONFIG,
    CONFIG_PATH,
    NETWORK_ITEM_LIST,
    NETWORK_LIST,
)
from ...tests.core.session import AkamaiSession
from ...tests.core.product import Akamai
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_OUTPUT = ActionOutput(
    output_message=(
        "Successfully connected to the Akamai server with the provided "
        "connection parameters!"
    ),
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)
PING_FAILED_OUTPUT = ActionOutput(
    output_message=(
        "Failed to connect to the Akamai server!\nReason: 'dict' object "
        "has no attribute 'suffix'"
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)

FAILED_CONFIG = CONFIG.copy()
FAILED_CONFIG["Host"] = "api.invalid.eu.test.com"


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping_success(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    akamai.add_network_lists(NETWORK_LIST)
    akamai.add_network_item_list(NETWORK_ITEM_LIST)

    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == PING_SUCCESS_OUTPUT


@set_metadata(integration_config_file_path=FAILED_CONFIG)
def test_ping_401_failure(
    akamai: Akamai,
    script_session: AkamaiSession,
    action_output: MockActionOutput,
) -> None:
    akamai.add_network_lists(NETWORK_LIST)
    akamai.add_network_item_list(NETWORK_ITEM_LIST)

    ping.main()

    assert len(script_session.request_history) == 0
    assert action_output.results == PING_FAILED_OUTPUT
