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

import json

import pytest
from actions.CreatePolicy import prepare_runner
from core.datamodels import Policy


@pytest.fixture(name="policy_data")
def mock_policy_data() -> dict:
    return {
        "type": "ADMIN",
        "customer": "customers/C01kec1yp",
        "policyQuery": {
            "query": "entity.org_units.exists(org_unit, "
                     "org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
            "orgUnit": "orgUnits/<ORG_UNIT_ID>",
        },
        "setting": {
            "type": "settings/rule.dlp",
            "value": {
                "display_name": "test_create_rule",
                "triggers": ["google.workspace.chrome.file.v1.download"],
                "state": "ACTIVE",
                "action": {"chromeAction": {"warnUser": {}}},
            },
        },
    }


def test_create_policy_success(action_context, api_manager, policy_data) -> None:
    # GIVEN
    action_context.action_parameters = {"Policy Entry": json.dumps(policy_data)}
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.create_policy.return_value = Policy.from_dict(policy_data)

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.create_policy.assert_called_once()
    assert result.value is True
    assert result.json_result == policy_data
    assert "Successfully added a new policy" in result.output_message


def test_create_policy_failure(action_context, api_manager, policy_data) -> None:
    # GIVEN
    action_context.action_parameters = {"Policy Entry": json.dumps(policy_data)}
    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.create_policy.side_effect = Exception("API error")

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.create_policy.assert_called_once()
    assert result.value is False
    assert (
        "Error executing action “Create Policy”. Reason: API error"
        in result.output_message
    )
