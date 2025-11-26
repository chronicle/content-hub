# Copyright 2025 Google LLC
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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import IpToInteger


@set_metadata(
    integration_config={},
    parameters={
        "IP Addresses": "192.168.1.1, 192.168.1.2",
    },
)
def test_ip_to_integer_json_result(action_output: MockActionOutput) -> None:
    IpToInteger.main()

    assert action_output.results.json_output.json_result == {
        "192.168.1.1": 3232235777,
        "192.168.1.2": 3232235778,
    }
    assert action_output.results.execution_state == ExecutionState.COMPLETED
