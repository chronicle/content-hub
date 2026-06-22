from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from actions.CreateIndicator import (
    SCRIPT_NAME,
    CreateIndicator,
    CreateIndicatorParameters,
)


class TestCreateIndicatorParameters:
    def test_parse_labels_from_csv(self):
        params = CreateIndicatorParameters(name="ind-1", pattern="[domain-name:value = 'example.org']", labels="l1, l2")
        assert params.labels == ["l1", "l2"]

    def test_parse_optional_dates(self):
        valid_from_iso = "2026-06-16T08:00:00+00:00"
        valid_until_iso = "2026-06-16T09:00:00+00:00"
        params = CreateIndicatorParameters(
            name="ind-1",
            pattern="[domain-name:value = 'example.org']",
            valid_from=valid_from_iso,
            valid_until=valid_until_iso,
        )
        assert isinstance(params.valid_from, datetime)
        assert isinstance(params.valid_until, datetime)
        assert params.valid_from.isoformat() == valid_from_iso
        assert params.valid_until.isoformat() == valid_until_iso

    def test_parse_optional_dates_google_soar_format(self):
        params = CreateIndicatorParameters(
            name="ind-1",
            pattern="[domain-name:value = 'example.org']",
            valid_from="2026-06-16 08:00:00 UTC+00",
            valid_until="2026-06-16 09:00:00 UTC+00",
        )
        assert isinstance(params.valid_from, datetime)
        assert isinstance(params.valid_until, datetime)
        assert params.valid_from.isoformat() == "2026-06-16T08:00:00+00:00"
        assert params.valid_until.isoformat() == "2026-06-16T09:00:00+00:00"

    def test_score_validation(self):
        with pytest.raises(ValueError):
            CreateIndicatorParameters(
                name="ind-1",
                pattern="[domain-name:value = 'example.org']",
                score=101,
            )

    def test_invalid_optional_date_raises_validation_error(self):
        with pytest.raises(ValueError):
            CreateIndicatorParameters(
                name="ind-1",
                pattern="[domain-name:value = 'example.org']",
                valid_from="not-a-date",
            )


class TestCreateIndicatorAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_action):
        mock_soar_action.parameters = {
            "Name": "ind-1",
            "Pattern": "[domain-name:value = 'example.org']",
            "Score": 50,
            "Valid From": "2026-06-16T08:00:00Z",
            "Valid Until": "2026-06-16T09:00:00Z",
        }

        action = CreateIndicator(SCRIPT_NAME)
        action._validate_params()

        assert action.params.name == "ind-1"
        assert action.params.score == 50
        assert action.params.valid_from is not None

    def test_perform_action_sets_output_message(self, mock_soar_action, mock_api_client):
        mock_soar_action.parameters = {
            "Name": "ind-1",
            "Pattern": "[domain-name:value = 'example.org']",
        }
        result_mock = MagicMock()
        result_mock.id = "ind-id-1"
        result_mock.json.return_value = {"id": "ind-id-1"}
        mock_api_client.create_indicator.return_value = result_mock

        action = CreateIndicator(SCRIPT_NAME)
        action.run()

        assert "ind-id-1" in action.output_message
        mock_api_client.create_indicator.assert_called_once()
