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

import pytest
from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import add_entity_to_detector_url_list
from cloud_identity.core.datamodels import Policy
from ..core.product import CloudIdentity
from ..core.session import CloudIdentitySession


@pytest.fixture(name="initial_policy_data")
def mock_initial_policy_data() -> dict:
    return {
        "type": "ADMIN",
        "customer": "customers/C01kec1yp",
        "name": "policies/policy_id",
        "policyQuery": {
            "query": "entity.org_units.exists(org_unit, org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
            "orgUnit": "orgUnits/<ORG_UNIT_ID>",
        },
        "setting": {
            "type": "settings/detector.url_list",
            "value": {
                "displayName": "test_url_list_detector",
                "description": "test_url_list_detector desc",
                "urlList": {
                    "urls": ["example.org", "bad_entity.com"],
                },
            },
        },
    }


class TestAddEntityToDetectorURLList:
    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "org_unit_name",
            "Detector Policy ID": "policy_id",
            "URL": "http://example.com, http://example2.com",
            "Domain": "example.org, example2.org",
        },
    )
    def test_add_entity_to_detector_url_list_success_params(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
        monkeypatch: pytest.MonkeyPatch,
        initial_policy_data: dict,
    ) -> None:
        monkeypatch.setattr(SiemplifyAction, "target_entities", [])

        # Setup initial policy state in mock product
        policy = Policy.from_dict(initial_policy_data)
        cloud_identity.add_policy(policy)

        add_entity_to_detector_url_list.main()

        # Verify REST calls were routed
        assert len(script_session.request_history) == 2
        req_get = script_session.request_history[0].request
        assert req_get.url.path.endswith("/policies/policy_id")
        assert req_get.method.value == "GET"

        req_patch = script_session.request_history[1].request
        assert req_patch.url.path.endswith("/policies/policy_id")
        assert req_patch.method.value == "PATCH"

        # Verify the updated policy url list in mock product
        updated_policy = cloud_identity.policies["policy_id"]
        updated_policy.match_setting_model()
        assert updated_policy.setting.value.url_list["urls"] == [
            "example.org",
            "bad_entity.com",
            "http://example.com",
            "http://example2.com",
            "example.org",
            "example2.org",
        ]

        assert action_output.results == ActionOutput(
            output_message="Successfully blocked the following URLs using Cloud Identity: http://example.com, http://example2.com, example.org, example2.org",
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(json_result=updated_policy.to_dict()),
        )

    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "org_unit_name",
            "Detector Policy ID": "policy_id",
        },
    )
    def test_add_entity_to_detector_url_list_success_entities(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
        monkeypatch: pytest.MonkeyPatch,
        initial_policy_data: dict,
    ) -> None:
        monkeypatch.setattr(
            SiemplifyAction,
            "target_entities",
            [
                create_entity("bad_entity1.com", EntityTypesEnum.URL),
                create_entity("bad_entity2.com", EntityTypesEnum.URL),
            ],
        )

        policy = Policy.from_dict(initial_policy_data)
        cloud_identity.add_policy(policy)

        add_entity_to_detector_url_list.main()

        assert len(script_session.request_history) == 2
        req_patch = script_session.request_history[1].request
        assert req_patch.method.value == "PATCH"

        updated_policy = cloud_identity.policies["policy_id"]
        updated_policy.match_setting_model()
        assert updated_policy.setting.value.url_list["urls"] == [
            "example.org",
            "bad_entity.com",
            "BAD_ENTITY1.COM",
            "BAD_ENTITY2.COM",
        ]

        assert action_output.results == ActionOutput(
            output_message="Successfully blocked the following URLs using Cloud Identity: BAD_ENTITY1.COM, BAD_ENTITY2.COM",
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(json_result=updated_policy.to_dict()),
        )

    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "org_unit_name",
            "Detector Policy ID": "policy_id",
        },
    )
    def test_add_entity_to_detector_url_list_no_input(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(SiemplifyAction, "target_entities", [])

        add_entity_to_detector_url_list.main()

        assert len(script_session.request_history) == 0

        assert action_output.results == ActionOutput(
            output_message="No entities, domains or url provided to block",
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config={
            "Delegated Email": "admin@example.com",
        },
        parameters={
            "Organization Unit Name": "org_unit_name",
            "Detector Policy ID": "policy_id",
            "URL": "http://example.com",
        },
    )
    def test_add_entity_to_detector_url_list_failure(
        self,
        script_session: CloudIdentitySession,
        action_output: MockActionOutput,
        cloud_identity: CloudIdentity,
        monkeypatch: pytest.MonkeyPatch,
        initial_policy_data: dict,
    ) -> None:
        monkeypatch.setattr(SiemplifyAction, "target_entities", [])

        policy = Policy.from_dict(initial_policy_data)
        cloud_identity.add_policy(policy)

        with cloud_identity.fail_requests():
            add_entity_to_detector_url_list.main()

        # The GET call to fetch_policy succeeds because fail_requests context manager is only entered right before the action starts?
        # Wait! "with cloud_identity.fail_requests():" wraps the entire main() execution, so the GET call to fetch_policy fails!
        # Yes! It will fail on the GET call first.
        assert len(script_session.request_history) == 1
        req_get = script_session.request_history[0].request
        assert req_get.method.value == "GET"

        assert action_output.results == ActionOutput(
            output_message=(
                'Error executing action "CloudIdentity - AddEntityToDetectorURLList"\n'
                "Reason: PoliciesApiResource failed reason: 500 Server Error: None for url: None, {'error': {'message': 'Simulated API failure'}}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
