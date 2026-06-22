from __future__ import annotations

from unittest.mock import MagicMock

from actions.CreateTool import SCRIPT_NAME, CreateTool, CreateToolParameters


class TestCreateToolParameters:
    def test_parse_csv_fields(self):
        params = CreateToolParameters(
            name="tool-1",
            tool_types="remote-access, exploitation",
            labels="l1, l2",
        )
        assert params.tool_types == ["remote-access", "exploitation"]
        assert params.labels == ["l1", "l2"]


class TestCreateToolAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "tool-1",
            "Tool Types": "remote-access",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }

        action = CreateTool(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "tool-1"
        assert action.params.tool_types == ["remote-access"]

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {"Name": "tool-1"}
        result_mock = MagicMock()
        result_mock.id = "tool-id-1"
        result_mock.json.return_value = {"id": "tool-id-1"}
        mock_api_client.create_tool.return_value = result_mock

        action = CreateTool(SCRIPT_NAME)
        action.run()

        assert "tool-id-1" in action.output_message
        mock_api_client.create_tool.assert_called_once()
