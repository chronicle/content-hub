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

from unittest.mock import MagicMock

import pytest
from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cloud_identity.actions import add_entity_to_detector_url_list
from cloud_identity.core.base_action import CloudIdentityAction
from cloud_identity.core.datamodels import Policy


@pytest.fixture(name="updated_policy_data")
def mock_updated_policy_data() -> dict:
    return {
        "type": "ADMIN",
        "customer": "customers/C01kec1yp",
        "policyQuery": {
            "query": "entity.org_units.exists(org_unit, "
                     "org_unit.org_unit_id == orgUnitId('<ORG_UNIT_ID>'))",
            "orgUnit": "orgUnits/<ORG_UNIT_ID>",
        },
        "setting": {
            "type": "settings/rule.urlListDetector",
            "value": {
                "display_name": "test_url_list_detector",
                "description": "test_url_list_detector desc",
                "triggers": ["google.workspace.chrome.file.v1.download"],
                "url_list": {
                    "urls": ["http://example.com", "example.org", "bad_entity.com"]
                },
            },
        },
    }


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
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    updated_policy_data: dict,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    monkeypatch.setattr(SiemplifyAction, "target_entities", [])
    api_manager.update_url_list_detector_policy.return_value = Policy.from_dict(
        updated_policy_data
    )

    add_entity_to_detector_url_list.main()

    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_called_once_with(
        policy_id="policy_id",
        urls=[
            "http://example.com",
            "http://example2.com",
            "example.org",
            "example2.org",
        ],
    )
    assert action_output.results == ActionOutput(
        output_message="Successfully blocked the following URLs using Cloud Identity: http://example.com, http://example2.com, example.org, example2.org",
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(json_result=updated_policy_data),
    )


@set_metadata(
    integration_config={
        "Delegated Email": "admin@example.com",
    },
    parameters={
        "Organization Unit Name": "org_unit_name",
        "Detector Policy ID": "policy_id",
    },
    entities=[
        create_entity("bad_entity1.com", EntityTypesEnum.URL),
        create_entity("bad_entity2.com", EntityTypesEnum.URL),
    ],
)
def test_add_entity_to_detector_url_list_success_entities(
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
    updated_policy_data: dict,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    monkeypatch.setattr(
        SiemplifyAction,
        "target_entities",
        [
            create_entity("bad_entity1.com", EntityTypesEnum.URL),
            create_entity("bad_entity2.com", EntityTypesEnum.URL),
        ],
    )
    api_manager.update_url_list_detector_policy.return_value = Policy.from_dict(
        updated_policy_data
    )

    add_entity_to_detector_url_list.main()

    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_called_once_with(
        policy_id="policy_id", urls=["BAD_ENTITY1.COM", "BAD_ENTITY2.COM"]
    )
    assert action_output.results == ActionOutput(
        output_message="Successfully blocked the following URLs using Cloud Identity: BAD_ENTITY1.COM, BAD_ENTITY2.COM",
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(json_result=updated_policy_data),
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
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    monkeypatch.setattr(SiemplifyAction, "target_entities", [])

    add_entity_to_detector_url_list.main()

    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_not_called()
    assert action_output.results == ActionOutput(
        output_message="No entities, domains or url provided to block",
        result_value=True,
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
    api_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    action_output: MockActionOutput,
) -> None:
    monkeypatch.setattr(CloudIdentityAction, "_get_api_manager", lambda _: api_manager)
    monkeypatch.setattr(SiemplifyAction, "target_entities", [])
    api_manager.update_url_list_detector_policy.side_effect = Exception("API error")

    add_entity_to_detector_url_list.main()

    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_called_once_with(
        policy_id="policy_id", urls=["http://example.com"]
    )
    assert action_output.results == ActionOutput(
        output_message=(
            'Error executing action "CloudIdentity - AddEntityToDetectorURLList"\n'
            "Reason: API error"
        ),
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
