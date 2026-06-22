from __future__ import annotations

from unittest.mock import MagicMock

from actions.CreateReport import SCRIPT_NAME, CreateReport, CreateReportParameters


class TestCreateReportParameters:
    def test_parse_csv_fields(self):
        params = CreateReportParameters(
            name="rep-1",
            publication_date="2026-06-16T10:00:00Z",
            report_types="threat-report, malware",
            labels="l1, l2",
        )
        assert params.report_types == ["threat-report", "malware"]
        assert params.labels == ["l1", "l2"]


class TestCreateReportAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "rep-1",
            "Publication Date": "2026-06-16T10:00:00Z",
            "Report types": "threat-report",
        }

        action = CreateReport(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "rep-1"
        assert action.params.report_types == ["threat-report"]

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "Name": "rep-1",
            "Publication Date": "2026-06-16T10:00:00Z",
            "Description": "desc",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
        }
        result_mock = MagicMock()
        result_mock.id = "rep-id-1"
        result_mock.json.return_value = {"id": "rep-id-1"}
        mock_api_client.create_report.return_value = result_mock

        action = CreateReport(SCRIPT_NAME)
        action.run()

        assert "rep-id-1" in action.output_message
        mock_api_client.create_report.assert_called_once()
