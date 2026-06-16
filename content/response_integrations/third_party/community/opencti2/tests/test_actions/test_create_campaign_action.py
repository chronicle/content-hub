from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateCampaign import SCRIPT_NAME, CreateCampaign, CreateCampaignParameters


class TestCreateCampaignParameters:
    def test_parse_labels_from_csv(self):
        params = CreateCampaignParameters(name="camp-1", labels="l1, l2")
        assert params.labels == ["l1", "l2"]

    def test_parse_optional_dates(self):
        first_seen_iso = "2026-06-16T08:00:00+00:00"
        last_seen_iso = "2026-06-16T09:00:00+00:00"
        params = CreateCampaignParameters(
            name="camp-1",
            first_seen=first_seen_iso,
            last_seen=last_seen_iso,
        )
        assert isinstance(params.first_seen, datetime)
        assert isinstance(params.last_seen, datetime)
        assert params.first_seen.isoformat() == first_seen_iso
        assert params.last_seen.isoformat() == last_seen_iso


class TestCreateCampaignAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "camp-1",
            "First Seen": "2026-06-16T08:00:00Z",
            "Last Seen": "2026-06-16T09:00:00Z",
        }

        action = CreateCampaign(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "camp-1"
        assert action.params.first_seen is not None

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {"Name": "camp-1"}
        result_mock = MagicMock()
        result_mock.id = "camp-id-1"
        result_mock.json.return_value = {"id": "camp-id-1"}
        mock_api_client.create_campaign.return_value = result_mock

        action = CreateCampaign(SCRIPT_NAME)
        action.run()

        assert "camp-id-1" in action.output_message
        mock_api_client.create_campaign.assert_called_once()
