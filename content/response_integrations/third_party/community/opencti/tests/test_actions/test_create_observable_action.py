from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from actions.CreateObservable import (
    SCRIPT_NAME,
    CreateObservable,
    CreateObservableParameters,
)


class TestCreateObservableParameters:
    def test_parse_labels_from_csv(self):
        params = CreateObservableParameters(
            observable_type="Domain Name",
            observable_value="google.com",
            labels="label1, label2",
        )
        assert params.labels == ["label1", "label2"]

    def test_validate_score_upper_bound(self):
        with pytest.raises(ValueError):
            CreateObservableParameters(
                observable_type="Domain Name",
                observable_value="google.com",
                score=101,
            )

    def test_validate_score_lower_bound(self):
        with pytest.raises(ValueError):
            CreateObservableParameters(
                observable_type="Domain Name",
                observable_value="google.com",
                score=-1,
            )


class TestCreateObservableAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Observable Type": "Domain Name",
            "Observable Value": "google.com",
            "Score": 50,
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Create Indicator": True,
        }

        action = CreateObservable(SCRIPT_NAME)
        action._validate_params()

        assert action.params.observable_type == "Domain Name"
        assert action.params.observable_value == "google.com"
        assert action.params.score == 50
        assert action.params.create_indicator is True

    def test_perform_action_sets_correct_observable_type(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "Observable Type": "Domain Name",
            "Observable Value": "google.com",
            "Score": 42,
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Create Indicator": True,
        }
        result_mock = MagicMock()
        result_mock.id = "obs-id-1"
        result_mock.json.return_value = {"id": "obs-id-1"}
        mock_api_client.create_observable.return_value = result_mock

        action = CreateObservable(SCRIPT_NAME)
        action.run()

        assert "obs-id-1" in action.output_message

        observable_obj = mock_api_client.create_observable.call_args.args[0]
        assert observable_obj.type == "Domain-Name"
        assert observable_obj.value == "google.com"
        assert observable_obj.score == 42
        assert observable_obj.labels == ["local", "test"]
        assert observable_obj.markings == ["TLP:AMBER"]
        assert observable_obj.create_indicator is True
