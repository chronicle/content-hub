from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from ...actions.CreateRequestForTakedown import (
    SCRIPT_NAME,
    CreateRequestForTakedown,
    CreateRequestForTakedownParameters,
)


class TestCreateRequestForTakedownParameters:
    def test_parse_labels_from_csv(self):
        params = CreateRequestForTakedownParameters(
            name="rft-1", labels="label1, label2"
        )
        assert params.labels == ["label1", "label2"]

    def test_created_defaults_to_aware_datetime(self):
        params = CreateRequestForTakedownParameters(name="rft-1")
        assert isinstance(params.created, datetime)
        assert params.created.tzinfo is not None


class TestCreateRequestForTakedownAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "rft-1",
            "Type": "Brand-abuse",
            "Severity": "low",
            "Created At": "2026-06-15T10:00:00Z",
        }

        action = CreateRequestForTakedown(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "rft-1"
        assert action.params.takedown_type == "Brand-abuse"
        assert action.params.severity == "low"

    def test_perform_action_sets_output_message(
        self, mock_soar_action, mock_api_client
    ):
        mock_soar_action.parameters = {
            "Name": "rft-1",
            "Description": "desc",
            "Severity": "low",
            "Type": "Brand-abuse",
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Created At": "2026-06-15T10:00:00Z",
        }
        result_mock = MagicMock()
        result_mock.id = "rft-id-1"
        result_mock.json.return_value = {"id": "rft-id-1"}
        mock_api_client.create_request_for_takedown.return_value = result_mock

        action = CreateRequestForTakedown(SCRIPT_NAME)
        action.run()

        assert "rft-id-1" in action.output_message

        obj = mock_api_client.create_request_for_takedown.call_args.args[0]
        assert obj.name == "rft-1"
        assert obj.takedown_types == ["Brand-abuse"]
        assert obj.severity == "low"
        assert obj.labels == ["local", "test"]
        assert obj.markings == ["TLP:AMBER"]
