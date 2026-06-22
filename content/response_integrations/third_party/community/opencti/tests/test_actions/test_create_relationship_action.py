from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateRelationship import (
    SCRIPT_NAME,
    CreateRelationship,
    CreateRelationshipParameters,
)


class TestCreateRelationshipParameters:
    def test_default_relationship_type(self):
        params = CreateRelationshipParameters(source_entity_id="a", target_entity_id="b")
        assert params.relationship_type == "related-to"

    def test_parse_first_seen_last_seen_google_soar_format(self):
        params = CreateRelationshipParameters(
            source_entity_id="a",
            target_entity_id="b",
            first_seen="2026-06-16 08:00:00 UTC+00",
            last_seen="2026-06-16 09:00:00 UTC+00",
        )
        assert isinstance(params.first_seen, datetime)
        assert isinstance(params.last_seen, datetime)
        assert params.first_seen.isoformat() == "2026-06-16T08:00:00+00:00"
        assert params.last_seen.isoformat() == "2026-06-16T09:00:00+00:00"


class TestCreateRelationshipAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Relationship Type": "uses",
            "Source Entity Id": "src-id",
            "Target Entity Id": "tgt-id",
            "First Seen": "2026-06-16T08:00:00Z",
            "Last Seen": "2026-06-16T09:00:00Z",
        }

        action = CreateRelationship(SCRIPT_NAME)
        action._validate_params()

        assert action.params.relationship_type == "uses"
        assert action.params.source_entity_id == "src-id"
        assert isinstance(action.params.first_seen, datetime)

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        first_seen_iso = "2026-06-16T08:00:00+00:00"
        last_seen_iso = "2026-06-16T09:00:00+00:00"
        mock_soar_action.parameters = {
            "Relationship Type": "uses",
            "Source Entity Id": "src-id",
            "Target Entity Id": "tgt-id",
            "First Seen": first_seen_iso,
            "Last Seen": last_seen_iso,
            "Marking": "TLP:AMBER",
        }
        result_mock = MagicMock()
        result_mock.id = "rel-id-1"
        result_mock.json.return_value = {"id": "rel-id-1"}
        mock_api_client.create_relationship.return_value = result_mock

        action = CreateRelationship(SCRIPT_NAME)
        action.run()

        assert "rel-id-1" in action.output_message

        relationship = mock_api_client.create_relationship.call_args.args[0]
        assert relationship.relationship_type == "uses"
        assert relationship.first_seen is not None
        assert relationship.last_seen is not None
