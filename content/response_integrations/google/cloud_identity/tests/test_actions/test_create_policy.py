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
import pytest

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import create_policy
from ..core.product import CloudIdentity
from ..core.session import CloudIdentitySession


@pytest.fixture(name="policy_data")
def mock_policy_data() -> dict:
    return {
        "type": "ADMIN",
        "customer": "customers/C01kec1yp",
        "policyQuery": {
            "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
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


class TestCreatePolicy:
    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Policy Entry": json.dumps({
                "type": "ADMIN",
                "customer": "customers/C01kec1yp",
                "policyQuery": {
                    "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
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
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
        policy_data: dict,
    ) -> None:
        create_policy.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/policies")
        assert request.method.value == "POST"

        # Verify the policy was persisted in the mock product
        created_policy = list(cloud_identity.policies.values())[0]
        assert created_policy.type == "ADMIN"
        assert created_policy.get_customer_id() == "C01kec1yp"

        expected_policy_response = policy_data.copy()
        expected_policy_response["name"] = created_policy.name

        assert action_output.results == ActionOutput(
            output_message="Successfully added a new policy in Cloud Identity.",
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(json_result=expected_policy_response),
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
                    "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
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
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
    ) -> None:
        with cloud_identity.fail_requests():
            create_policy.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/policies")

        assert action_output.results == ActionOutput(
            output_message=(
                'Error executing action "CloudIdentity - CreatePolicy"\n'
                "Reason: PoliciesApiResource failed reason: 500 Server Error: None for url: None, {'error': {'message': 'Simulated API failure'}}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
