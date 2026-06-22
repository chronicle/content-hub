from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateIncidentResponse import (
    SCRIPT_NAME,
    CreateIncidentResponse,
    CreateIncidentResponseParameters,
)


class TestCreateIncidentResponseParameters:
    def test_parse_labels_from_csv(self):
        params = CreateIncidentResponseParameters(
            name="case-1", labels="label1, label2"
        )
        assert params.labels == ["label1", "label2"]

    def test_created_defaults_to_aware_datetime(self):
        params = CreateIncidentResponseParameters(name="case-1")
        assert isinstance(params.created, datetime)
        assert params.created.tzinfo is not None


class TestCreateIncidentResponseAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "case-1",
            "Type": "Alert",
            "Severity": "high",
            "Priority": "p1",
            "Created At": "2026-06-15T10:00:00Z",
        }

        action = CreateIncidentResponse(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "case-1"
        assert action.params.response_type == "Alert"
        assert action.params.priority == "p1"

    def test_perform_action_sets_output_message(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {
            "Name": "case-1",
            "Description": "desc",
            "Severity": "high",
            "Priority": "p1",
            "Type": "Alert",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Created At": "2026-06-15T10:00:00Z",
        }
        result_mock = MagicMock()
        result_mock.id = "case-id-1"
        result_mock.json.return_value = {"id": "case-id-1"}
        mock_api_client.create_incident_response.return_value = result_mock

        action = CreateIncidentResponse(SCRIPT_NAME)
        action.run()

        assert "case-id-1" in action.output_message

        obj = mock_api_client.create_incident_response.call_args.args[0]
        assert obj.name == "case-1"
        assert obj.response_types == ["Alert"]
        assert obj.priority == "p1"
        assert obj.severity == "high"
        assert obj.labels == ["local", "test"]
        assert obj.markings == ["TLP:AMBER"]
