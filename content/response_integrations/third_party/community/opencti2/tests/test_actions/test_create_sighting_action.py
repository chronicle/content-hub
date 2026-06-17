from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateSighting import SCRIPT_NAME, CreateSighting, CreateSightingParameters


class TestCreateSightingParameters:
    def test_parse_labels_from_csv(self):
        params = CreateSightingParameters(from_object_id="from-id", to_object_id="to-id", labels="l1, l2")
        assert params.labels == ["l1", "l2"]

    def test_parse_optional_dates(self):
        first_seen_iso = "2026-06-16T08:00:00+00:00"
        last_seen_iso = "2026-06-16T09:00:00+00:00"
        params = CreateSightingParameters(
            from_object_id="from-id",
            to_object_id="to-id",
            first_seen=first_seen_iso,
            last_seen=last_seen_iso,
        )
        assert isinstance(params.first_seen, datetime)
        assert isinstance(params.last_seen, datetime)
        assert params.first_seen.isoformat() == first_seen_iso
        assert params.last_seen.isoformat() == last_seen_iso


class TestCreateSightingAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "From Object Id": "from-id",
            "To Object Id": "to-id",
            "First Seen": "2026-06-16T08:00:00Z",
            "Last Seen": "2026-06-16T09:00:00Z",
        }

        action = CreateSighting(SCRIPT_NAME)
        action._validate_params()

        assert action.params.from_object_id == "from-id"
        assert action.params.to_object_id == "to-id"
        assert action.params.first_seen is not None

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "From Object Id": "from-id",
            "To Object Id": "to-id",
            "First Seen": "2026-06-16T08:00:00+00:00",
            "Last Seen": "2026-06-16T09:00:00+00:00",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }
        result_mock = MagicMock()
        result_mock.id = "sighting-id-1"
        result_mock.json.return_value = {"id": "sighting-id-1"}
        mock_api_client.create_sighting.return_value = result_mock

        action = CreateSighting(SCRIPT_NAME)
        action.run()

        assert "sighting-id-1" in action.output_message
        mock_api_client.create_sighting.assert_called_once()
