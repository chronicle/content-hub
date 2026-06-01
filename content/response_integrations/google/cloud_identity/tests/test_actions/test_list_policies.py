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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import list_policies
from cloud_identity.core.datamodels import OrgUnit, Policy
from ..core.product import CloudIdentity
from ..core.session import CloudIdentitySession


class TestListPolicies:
    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "TestOrgName",
            "Policy Type Filter": "ADMIN",
            "Setting Type Filter": "settings/rule.dlp",
            "Settings Display Name Filter": "Display name, Display name 2",
            "Max Results To Return": 3,
        },
    )
    def test_list_policies_success(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
    ) -> None:
        # 1. Setup the in-memory OrgUnit in the product mock
        org_unit = OrgUnit.from_dict({
            "name": "TestOrgName",
            "orgUnitId": "orgUnits/Id",
            "orgUnitPath": "/TestOrgName",
        })
        cloud_identity.add_org_unit(org_unit)

        # 2. Setup the in-memory Policy in the product mock matching the criteria
        policy = Policy.from_dict({
            "type": "ADMIN",
            "customer": "customers/C01kec1yp",
            "name": "policies/TestName",
            "policyQuery": {
                "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('Id'))",
                "orgUnit": "orgUnits/Id",
            },
            "setting": {
                "type": "settings/rule.dlp",
                "value": {
                    "displayName": "Display name",
                },
            },
        })
        cloud_identity.add_policy(policy)

        list_policies.main()

        # Verify correct REST requests were routed
        # First, it should list org units to find the ID
        # Second, it should list policies
        assert len(script_session.request_history) == 2
        req_org = script_session.request_history[0].request
        assert "/orgunits" in req_org.url.path

        req_pol = script_session.request_history[1].request
        assert req_pol.url.path.endswith("/policies")
        assert req_pol.kwargs["params"]["filter"] == 'setting.type.matches("settings/rule.dlp")'

        assert action_output.results == ActionOutput(
            output_message="Successfully listed policies based on the provided criteria in Cloud Identity.",
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(json_result=[policy.to_dict()]),
        )

    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "TestOrgName",
            "Policy Type Filter": "ADMIN",
            "Setting Type Filter": "settings/rule.dlp",
            "Settings Display Name Filter": "Display name, Display name 2",
            "Max Results To Return": 3,
        },
    )
    def test_list_policies_failure(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
    ) -> None:
        # Populate OrgUnit so the lookup succeeds and failure happens during list_policies itself
        org_unit = OrgUnit.from_dict({
            "name": "TestOrgName",
            "orgUnitId": "orgUnits/Id",
            "orgUnitPath": "/TestOrgName",
        })
        cloud_identity.add_org_unit(org_unit)

        with cloud_identity.fail_requests():
            list_policies.main()

        assert action_output.results == ActionOutput(
            output_message=(
                'Error executing action "CloudIdentity - ListPolicies"\n'
                "Reason: OrgUnitsApiResource failed reason: 500 Server Error: None for url: None, {'error': {'message': 'Simulated API failure'}}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
