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

from unittest.mock import Mock

import pytest
from actions.AddEntityToDetectorURLList import (
    prepare_runner,
)
from core.datamodels import Policy


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


def test_add_entity_to_detector_url_list_success_params(
    action_context, api_manager, updated_policy_data
) -> None:
    # GIVEN
    action_context.action_parameters = {
        "Organization Unit Name": "org_unit_name",
        "Detector Policy ID": "policy_id",
        "URL": ["http://example.com", "http://example2.com"],
        "Domain": ["example.org", "example2.org"],
    }

    # Mock entities to return nothing for this test
    action_context.get_entities = Mock(return_value=[])

    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.update_url_list_detector_policy.return_value = Policy.from_dict(
        updated_policy_data
    )

    # WHEN
    result = runner.run(action_context)

    # THEN
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
    assert result.value is True
    assert result.json_result == updated_policy_data
    assert "Successfully blocked the following URLs" in result.output_message


def test_add_entity_to_detector_url_list_success_entities(
    action_context, api_manager, updated_policy_data
) -> None:
    # GIVEN
    action_context.action_parameters = {
        "Organization Unit Name": "org_unit_name",
        "Detector Policy ID": "policy_id",
    }

    # Mock entities
    mock_entity1 = Mock()
    mock_entity1.identifier = "bad_entity1.com"
    mock_entity2 = Mock()
    mock_entity2.identifier = "bad_entity2.com"

    action_context.get_entities = Mock(return_value=[mock_entity1, mock_entity2])

    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.update_url_list_detector_policy.return_value = Policy.from_dict(
        updated_policy_data
    )

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_called_once_with(
        policy_id="policy_id", urls=["bad_entity1.com", "bad_entity2.com"]
    )
    assert result.value is True
    assert result.json_result == updated_policy_data
    assert "Successfully blocked the following URLs" in result.output_message


def test_add_entity_to_detector_url_list_no_input(action_context, api_manager) -> None:
    # GIVEN
    action_context.action_parameters = {
        "Organization Unit Name": "org_unit_name",
        "Detector Policy ID": "policy_id",
    }

    action_context.get_entities = Mock(return_value=[])

    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_not_called()
    assert result.value is True
    assert result.output_message == "No entities, domains or url provided to block"


def test_add_entity_to_detector_url_list_failure(
    action_context, api_manager
) -> None:
    # GIVEN
    action_context.action_parameters = {
        "Organization Unit Name": "org_unit_name",
        "Detector Policy ID": "policy_id",
        "URL": ["http://example.com"],
    }

    action_context.get_entities = Mock(return_value=[])

    runner = prepare_runner()
    runner.register_injectable("api_manager", api_manager)
    api_manager.update_url_list_detector_policy.side_effect = Exception("API error")

    # WHEN
    result = runner.run(action_context)

    # THEN
    api_manager.test_connectivity.assert_called_once()
    api_manager.update_url_list_detector_policy.assert_called_once_with(
        policy_id="policy_id", urls=["http://example.com"]
    )
    assert result.value is False
    assert (
        "Error executing action “Add Entity To Detector URL List”. Reason: API error"
        in result.output_message
    )
