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

from unittest.mock import MagicMock, patch

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from TIPCommon.base.action import ExecutionState

from ...actions.CreateEntityRelationships import CreateEntityRelationshipsAction


class MockedCreateEntityRelationshipsAction(CreateEntityRelationshipsAction):
    def __init__(self, mock_siemplify):
        super().__init__()
        self._soar_action = mock_siemplify


@set_metadata(
    integration_config={},
    parameters={
        "Separator Character": ",",
        "Entity Identifier(s)": "entity1, entity2",
        "Target Entity Identifier(s)": "target1, target2",
        "Target Entity Type": "USER",
        "Entity Identifier(s) Type": "USER",
        "Connect As": "Linked",
        "Enrichment JSON": "{}",
    },
)
@patch("TIPCommon.rest.soar_api.create_entity")
def test_create_entity_relationships_success(
    mock_create_entity: MagicMock,
    action_output: MockActionOutput,
) -> None:
    mock_siemplify: MagicMock = MagicMock()
    mock_siemplify.load_case_data.return_value = None
    
    mock_siemplify.parameters = {
        "Separator Character": ",",
        "Entity Identifier(s)": "entity1, entity2",
        "Target Entity Identifier(s)": "target1, target2",
        "Target Entity Type": "USER",
        "Entity Identifier(s) Type": "USER",
        "Connect As": "Linked",
        "Enrichment JSON": "{}",
    }
    
    mock_alert: MagicMock = MagicMock()
    mock_alert.identifier = "alert1"
    mock_alert.entities = []
    mock_siemplify.current_alert = mock_alert
    mock_siemplify.case_id = "123"
    
    mock_case: MagicMock = MagicMock()
    mock_case.alerts = [mock_alert]
    mock_siemplify.case = mock_case
    
    action: MockedCreateEntityRelationshipsAction = MockedCreateEntityRelationshipsAction(mock_siemplify)
    
    with patch.object(CreateEntityRelationshipsAction, "_get_target_alerts", return_value=[mock_alert]):
        action.run()
    
    assert action.execution_state == ExecutionState.COMPLETED
