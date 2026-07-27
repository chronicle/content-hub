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
from TIPCommon.base.data_models import ActionOutput
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import ping
from cloud_identity.core.datamodels import Policy
from ..core.product import CloudIdentity
from ..core.session import CloudIdentitySession


class TestPing:
    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        }
    )
    def test_ping_success(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
    ) -> None:
        # Populating at least one policy in-memory so that test_connectivity list() iterator is not empty.
        policy = Policy.from_dict({
            "type": "ADMIN",
            "customer": "customers/C01kec1yp",
            "name": "policies/test_policy_id",
            "policyQuery": {
                "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
                "orgUnit": "orgUnits/<ORG_UNIT_ID>",
            },
            "setting": {
                "type": "settings/rule.dlp",
                "value": {
                    "displayName": "test_create_rule",
                },
            },
        })
        cloud_identity.add_policy(policy)

        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/policies")
        assert request.kwargs["params"]["pageSize"] == 1

        assert action_output.results == ActionOutput(
            output_message=(
                "Successfully connected to the Cloud Identity server with "
                "the provided connection parameters!"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        }
    )
    def test_ping_failure(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
    ) -> None:
        with cloud_identity.fail_requests():
            ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/policies")

        assert action_output.results == ActionOutput(
            output_message=(
                "Failed to connect to the Cloud Identity server!\n"
                "Reason: PoliciesApiResource failed reason: 500 Server Error: None for url: None, {'error': {'message': 'Simulated API failure'}}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
