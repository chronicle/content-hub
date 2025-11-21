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

from ...actions import ExtractIocs


@set_metadata(
    integration_config={},
    parameters={
        "Input String": (
            "Your account has been locked due to suspicious activity from 1.2.3.4. "
            "Immediately send a confirmation email to security.alert@micr0soft.com "
            "or click on the link: https://micr0soft.com/me/keep-data before "
            "your data is lost forever."
        ),
    },
)
def test_extract_iocs_json_result(action_output: MockActionOutput) -> None:
    ExtractIocs.main()

    assert action_output.results.json_output.json_result == {
        "domains": ["micr0soft.com"],
        "emails": ["security.alert@micr0soft.com"],
        "ips": ["1.2.3.4"],
        "urls": ["https://micr0soft.com/me/keep-data"]
    }
    assert action_output.results.execution_state == ExecutionState.COMPLETED
