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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import EntityTypes
from anomali_threat_stream.actions.EnrichEntities import main


def test_enrich_entities_success(
    monkeypatch, action_output, json_results, mock_siemplify
):
    # Setup mock entities
    mock_entity = MagicMock()
    mock_entity.entity_type = EntityTypes.URL
    mock_entity.identifier = "https://google.com"
    mock_entity.additional_properties = {}

    mock_siemplify.target_entities = [mock_entity]
    mock_siemplify.action_params = {
        "Severity Threshold": "Low",
        "Confidence Threshold": 50,
        "Ignore False Positive Status": False,
        "Create Insight": False,
    }

    # Mock AnomaliManager
    mock_manager = MagicMock()

    # Mock indicators returned by manager
    mock_indicator = MagicMock()
    mock_indicator.as_json.return_value = {
        "id": 1,
        "type": "url",
        "url": "https://google.com",
    }

    # Mock indicator group
    mock_group = MagicMock()
    mock_group.entity = mock_entity
    mock_group.indicators = [mock_indicator]
    mock_group.is_false_positive = False
    mock_group.numeric_severity = 2  # 'medium' which is > 'low' (1)
    mock_group.confidence = 100
    mock_group.as_enrichment.return_value = {"enriched": "true"}
    mock_group.as_csv.return_value = {"csv": "data"}

    mock_manager.get_indicators.return_value = [mock_indicator]
    mock_manager.parser.match_entity_to_indicators.return_value = [mock_group]

    # Patch AnomaliManager in EnrichEntities
    monkeypatch.setattr(
        "anomali_threat_stream.actions.EnrichEntities.AnomaliManager",
        lambda **kwargs: mock_manager,
    )

    # Run action
    main()

    # Assert results
    assert action_output.status == EXECUTION_STATE_COMPLETED
    assert action_output.is_success is True

    # Check JSON results
    results = json_results.json_results
    assert "results" in results
    assert isinstance(results["results"], list)
    assert len(results["results"]) == 1
    assert results["results"][0]["Entity"] == "https://google.com"
    assert results["results"][0]["EntityResult"][0]["is_risky"] is True
