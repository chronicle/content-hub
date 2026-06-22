from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from actions.CreateIncident import SCRIPT_NAME, CreateIncident, CreateIncidentParameters


class TestCreateIncidentParameters:
    def test_parse_labels_from_csv(self):
        params = CreateIncidentParameters(name="incident-1", labels="label1, label2")
        assert params.labels == ["label1", "label2"]

    def test_created_defaults_to_aware_datetime(self):
        params = CreateIncidentParameters(name="incident-1")
        assert isinstance(params.created, datetime)
        assert params.created.tzinfo is not None

    def test_created_accepts_google_soar_format(self):
        params = CreateIncidentParameters(
            name="incident-1",
            created="2026-06-16 08:00:00 UTC+00",
        )
        assert isinstance(params.created, datetime)
        assert params.created.isoformat() == "2026-06-16T08:00:00+00:00"


class TestCreateIncidentAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "incident-1",
            "Description": "desc",
            "Type": "Ransomware",
            "Severity": "high",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Created At": "2026-06-15T10:00:00Z",
        }

        action = CreateIncident(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "incident-1"
        assert action.params.incident_type == "Ransomware"
        assert action.params.severity == "high"
        assert action.params.labels == ["local", "test"]

    def test_perform_action_sets_output_message_and_json_results(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {
            "Name": "incident-1",
            "Description": "desc",
            "Type": "Ransomware",
            "Severity": "high",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }
        result_mock = MagicMock()
        result_mock.id = "inc-id-1"
        result_mock.json.return_value = {"id": "inc-id-1"}
        mock_api_client.create_incident.return_value = result_mock

        action = CreateIncident(SCRIPT_NAME)
        action.run()

        assert "inc-id-1" in action.output_message
        assert action.json_results == {"id": "inc-id-1"}

        incident_obj = mock_api_client.create_incident.call_args.args[0]
        assert incident_obj.name == "incident-1"
        assert incident_obj.description == "desc"
        assert incident_obj.incident_type == "Ransomware"
        assert incident_obj.severity == "high"
        assert incident_obj.labels == ["local", "test"]
        assert incident_obj.markings == ["TLP:AMBER"]

    def test_created_at_defaults_when_not_provided(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {"Name": "incident-1"}
        result_mock = MagicMock()
        result_mock.id = "inc-id-2"
        result_mock.json.return_value = {}
        mock_api_client.create_incident.return_value = result_mock

        action = CreateIncident(SCRIPT_NAME)
        action.run()

        incident_obj = mock_api_client.create_incident.call_args.args[0]
        assert incident_obj.created is not None
        assert incident_obj.created.tzinfo is not None
