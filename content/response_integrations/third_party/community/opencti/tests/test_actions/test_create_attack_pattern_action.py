from __future__ import annotations

from unittest.mock import MagicMock

from actions.CreateAttackPattern import (
    SCRIPT_NAME,
    CreateAttackPattern,
    CreateAttackPatternParameters,
)


class TestCreateAttackPatternParameters:
    def test_parse_labels_from_csv(self):
        params = CreateAttackPatternParameters(name="ap-1", labels="l1, l2")
        assert params.labels == ["l1", "l2"]


class TestCreateAttackPatternAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "ap-1",
            "Description": "desc",
            "External Id": "T0001",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }

        action = CreateAttackPattern(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "ap-1"
        assert action.params.external_id == "T0001"
        assert action.params.labels == ["local", "test"]

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {"Name": "ap-1"}
        result_mock = MagicMock()
        result_mock.id = "ap-id-1"
        result_mock.json.return_value = {"id": "ap-id-1"}
        mock_api_client.create_attack_pattern.return_value = result_mock

        action = CreateAttackPattern(SCRIPT_NAME)
        action.run()

        assert "ap-id-1" in action.output_message
        mock_api_client.create_attack_pattern.assert_called_once()
