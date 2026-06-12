from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateRequestForInformation import (
    SCRIPT_NAME,
    CreateRequestForInformation,
    CreateRequestForInformationParameters,
)


class TestCreateRequestForInformationParameters:
    def test_parse_labels_from_csv(self):
        params = CreateRequestForInformationParameters(name="rfi-1", labels="label1, label2")
        assert params.labels == ["label1", "label2"]

    def test_created_defaults_to_aware_datetime(self):
        params = CreateRequestForInformationParameters(name="rfi-1")
        assert isinstance(params.created, datetime)
        assert params.created.tzinfo is not None


class TestCreateRequestForInformationAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "rfi-1",
            "Type": "Fraud",
            "Severity": "medium",
            "Created At": "2026-06-15T10:00:00Z",
        }

        action = CreateRequestForInformation(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "rfi-1"
        assert action.params.rfi_type == "Fraud"
        assert action.params.severity == "medium"

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "Name": "rfi-1",
            "Description": "desc",
            "Severity": "medium",
            "Type": "Fraud",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Created At": "2026-06-15T10:00:00Z",
        }
        result_mock = MagicMock()
        result_mock.id = "rfi-id-1"
        result_mock.json.return_value = {"id": "rfi-id-1"}
        mock_api_client.create_request_for_information.return_value = result_mock

        action = CreateRequestForInformation(SCRIPT_NAME)
        action.run()

        assert "rfi-id-1" in action.output_message

        obj = mock_api_client.create_request_for_information.call_args.args[0]
        assert obj.name == "rfi-1"
        assert obj.information_types == ["Fraud"]
        assert obj.severity == "medium"
        assert obj.labels == ["local", "test"]
        assert obj.markings == ["TLP:AMBER"]
