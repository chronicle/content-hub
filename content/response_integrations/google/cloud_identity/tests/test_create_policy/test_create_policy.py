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

import json
from unittest.mock import MagicMock

import pytest
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import create_policy
from cloud_identity.core.base_action import CloudIdentityAction
from cloud_identity.core.datamodels import Policy


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


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    },
    parameters={
        "Policy Entry": json.dumps({
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
        }),
    },
)
def test_create_policy_success(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    policy_data: dict,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    api_manager.create_policy.return_value = Policy.from_dict(policy_data)

    create_policy.main()

    api_manager.create_policy.assert_called_once()
    assert action_output.results == ActionOutput(
        output_message="Successfully added a new policy in Cloud Identity.",
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(json_result=policy_data),
    )


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    },
    parameters={
        "Policy Entry": json.dumps({
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
        }),
    },
)
def test_create_policy_failure(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    api_manager.create_policy.side_effect = Exception("API error")

    create_policy.main()

    api_manager.create_policy.assert_called_once()
    assert action_output.results == ActionOutput(
        output_message=(
            'Error executing action "CloudIdentity - CreatePolicy"\n'
            "Reason: API error"
        ),
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
