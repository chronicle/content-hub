from __future__ import annotations

from unittest.mock import MagicMock

from actions.CreateGrouping import SCRIPT_NAME, CreateGrouping, CreateGroupingParameters


class TestCreateGroupingParameters:
    def test_parse_labels_from_csv(self):
        params = CreateGroupingParameters(
            name="group-1", context="Suspicious activity", labels="l1, l2"
        )
        assert params.labels == ["l1", "l2"]


class TestCreateGroupingAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "group-1",
            "Context": "Suspicious activity",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }

        action = CreateGrouping(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "group-1"
        assert action.params.context == "Suspicious activity"

    def test_perform_action_passes_mapped_context_to_client(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {
            "Name": "group-1",
            "Context": "Suspicious activity",
        }
        result_mock = MagicMock()
        result_mock.id = "group-id-1"
        result_mock.json.return_value = {"id": "group-id-1"}
        mock_api_client.create_grouping.return_value = result_mock

        action = CreateGrouping(SCRIPT_NAME)
        action.run()

        grouping_obj = mock_api_client.create_grouping.call_args.args[0]
        assert grouping_obj.context == "Suspicious activity"
        assert "group-id-1" in action.output_message
