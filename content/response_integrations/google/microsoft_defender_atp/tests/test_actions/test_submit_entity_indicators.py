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

from TIPCommon.base.action import ExecutionState, EntityTypesEnum

from microsoft_defender_atp.actions import SubmitEntityIndicators

from microsoft_defender_atp.tests import common
from microsoft_defender_atp.tests.core.product import MicrosoftDefenderATP
from microsoft_defender_atp.tests.core.session import (
    MicrosoftDefenderATPSession,
)
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

IP_ENTITY = create_entity(identifier="1.2.3.4", type_=EntityTypesEnum.ADDRESS)
SHA256_HASH = "a" * 64
SHA256_ENTITY = create_entity(identifier=SHA256_HASH, type_=EntityTypesEnum.FILE_HASH)
URL_ENTITY = create_entity(identifier="http://malicious.example.com", type_=EntityTypesEnum.URL)

DEFAULT_PARAMS = {
    "Action": "Alert",
    "Severity": "High",
    "Application": "",
    "Indicator Alert Title": "Test Indicator",
    "Description": "Test description",
    "Recommended Action": "",
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[IP_ENTITY, SHA256_ENTITY],
)
def test_submit_entity_indicators_success(
    _microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that new indicators are successfully submitted."""
    SubmitEntityIndicators.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    assert "Successfully submitted" in action_output.results.output_message


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[IP_ENTITY],
)
def test_submit_entity_indicators_already_exists(
    microsoft_defender_atp: MicrosoftDefenderATP,
    _script_session: MicrosoftDefenderATPSession,
    action_output: MockActionOutput,
) -> None:
    """Test that existing indicators are reported as already present."""
    microsoft_defender_atp.add_indicator(
        {
            "id": "existing-1",
            "indicatorValue": "1.2.3.4",
            "indicatorType": "IpAddress",
            "action": "Alert",
            "severity": "High",
        }
    )

    SubmitEntityIndicators.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value in (True, "true")
    output = action_output.results.output_message
    assert "already indicators" in output
