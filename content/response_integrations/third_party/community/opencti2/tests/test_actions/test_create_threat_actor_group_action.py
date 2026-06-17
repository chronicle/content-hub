from __future__ import annotations

from unittest.mock import MagicMock

from actions.CreateThreatActorGroup import (
    SCRIPT_NAME,
    CreateThreatActorGroup,
    CreateThreatActorGroupParameters,
)


class TestCreateThreatActorGroupParameters:
    def test_parse_csv_fields(self):
        params = CreateThreatActorGroupParameters(
            name="tag-1",
            threat_actor_types="crime-syndicate, nation-state",
            labels="l1, l2",
        )
        assert params.threat_actor_types == ["crime-syndicate", "nation-state"]
        assert params.labels == ["l1", "l2"]


class TestCreateThreatActorGroupAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "tag-1",
            "Threat Actor Types": "crime-syndicate",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }

        action = CreateThreatActorGroup(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "tag-1"
        assert action.params.threat_actor_types == ["crime-syndicate"]

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {"Name": "tag-1"}
        result_mock = MagicMock()
        result_mock.id = "tag-id-1"
        result_mock.json.return_value = {"id": "tag-id-1"}
        mock_api_client.create_threat_actor_group.return_value = result_mock

        action = CreateThreatActorGroup(SCRIPT_NAME)
        action.run()

        assert "tag-id-1" in action.output_message
        mock_api_client.create_threat_actor_group.assert_called_once()
