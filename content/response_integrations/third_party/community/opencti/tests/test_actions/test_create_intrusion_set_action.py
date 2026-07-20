from __future__ import annotations

from unittest.mock import MagicMock

from ...actions.CreateIntrusionSet import (
    SCRIPT_NAME,
    CreateIntrusionSet,
    CreateIntrusionSetParameters,
)


class TestCreateIntrusionSetParameters:
    def test_parse_labels_from_csv(self):
        params = CreateIntrusionSetParameters(name="is-1", labels="l1, l2")
        assert params.labels == ["l1", "l2"]


class TestCreateIntrusionSetAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "is-1",
            "Description": "desc",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }

        action = CreateIntrusionSet(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "is-1"
        assert action.params.labels == ["local", "test"]

    def test_perform_action_sets_output_message(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {"Name": "is-1"}
        result_mock = MagicMock()
        result_mock.id = "is-id-1"
        result_mock.json.return_value = {"id": "is-id-1"}
        mock_api_client.create_intrusion_set.return_value = result_mock

        action = CreateIntrusionSet(SCRIPT_NAME)
        action.run()

        assert "is-id-1" in action.output_message
        mock_api_client.create_intrusion_set.assert_called_once()
