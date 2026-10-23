# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the Calculate Risk Score action."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from xm_cyber.actions import CalculateRiskScore
from xm_cyber.core.constants import (
    ENRICHED_ENTITY_ID_FIELD,
    PREFIX_PARAMETER_FOR_ENTITY_ID,
    PREFIX_PARAMETER_FOR_LABELS,
)

CONFIGURED_PARAMS = {
    "is_critical_asset": "Default",
    "is_predefined_admin": "Default",
    "is_highly_privileged": "Default",
    "ad_risk_to_domain": "Default",
    "ad_risky_principals": "Default",
    "ad_admins_and_dcs": "Default",
    "user_without_mfa": "Default",
    "choke_point_score": "Default",
    "compromise_risk_score": "Default",
}


def _entity_properties(choke_point_score: str, compromise_risk_score: str) -> dict[str, str]:
    """Build XM Cyber enriched entity properties with the given score values."""
    return {
        ENRICHED_ENTITY_ID_FIELD: "entity-1",
        PREFIX_PARAMETER_FOR_ENTITY_ID.format("Entity Type"): "Device",
        PREFIX_PARAMETER_FOR_ENTITY_ID.format("Choke Point Score"): choke_point_score,
        PREFIX_PARAMETER_FOR_ENTITY_ID.format("Compromise Risk Score"): compromise_risk_score,
    }


@pytest.mark.parametrize("bad_value", ["", "N/A", "None", "high"])
def test_non_numeric_scores_do_not_crash_and_count_as_zero(bad_value: str) -> None:
    """Non-numeric scores are treated as 0 instead of raising."""
    result = CalculateRiskScore.calculate_risk_score_for_entity(
        _entity_properties(bad_value, bad_value), CONFIGURED_PARAMS
    )

    assert result["compromised_choke_point_score"] == 0
    assert result["compromised_risk_score"] == 0


def test_numeric_scores_are_preserved() -> None:
    """Numeric string scores are converted and reported."""
    result = CalculateRiskScore.calculate_risk_score_for_entity(
        _entity_properties("40", "25"), CONFIGURED_PARAMS
    )

    assert result["compromised_choke_point_score"] == 40
    assert result["compromised_risk_score"] == 25


@pytest.mark.parametrize("flag_value", ["TRUE", "True", "true", " true ", True])
def test_flag_matches_true_in_any_case(flag_value: str | bool) -> None:
    """Boolean flags add their score regardless of how the value is capitalized."""
    components = [("Is Critical Asset", 0.2)]

    entity_score = CalculateRiskScore.calculate_score(
        {PREFIX_PARAMETER_FOR_ENTITY_ID.format("Is Critical Asset"): flag_value}, components
    )
    event_score = CalculateRiskScore.calculate_score(
        {PREFIX_PARAMETER_FOR_LABELS.format("asset", "Is Critical Asset"): flag_value},
        components,
        "asset",
    )

    assert entity_score == pytest.approx(1.2)
    assert event_score == pytest.approx(1.2)


@pytest.mark.parametrize("flag_value", ["FALSE", "False", "false", "", "N/A", False])
def test_flag_not_true_adds_nothing(flag_value: str | bool) -> None:
    """Values other than true do not add to the score."""
    score = CalculateRiskScore.calculate_score(
        {PREFIX_PARAMETER_FOR_ENTITY_ID.format("Is Critical Asset"): flag_value},
        [("Is Critical Asset", 0.2)],
    )

    assert score == 1


def test_flag_missing_adds_nothing() -> None:
    """A property that is absent does not add to the score."""
    assert CalculateRiskScore.calculate_score({}, [("Is Critical Asset", 0.2)]) == 1


def test_custom_value_to_check_is_case_insensitive() -> None:
    """A component with an explicit value to match is compared case-insensitively."""
    score = CalculateRiskScore.calculate_score(
        {PREFIX_PARAMETER_FOR_ENTITY_ID.format("Tier"): "gold"}, [("Tier", 0.5, "GOLD")]
    )

    assert score == pytest.approx(1.5)


def _run_main(entities: list[MagicMock]) -> MagicMock:
    """Run main() with a mocked SiemplifyAction holding the given entities."""
    siemplify = MagicMock()
    siemplify.current_alert.security_events = []
    siemplify.target_entities = entities
    siemplify.extract_action_param.side_effect = (
        lambda _name, default_value=None, **_kwargs: default_value
    )

    with patch.object(CalculateRiskScore, "SiemplifyAction", return_value=siemplify):
        CalculateRiskScore.main()

    return siemplify


def test_main_flags_missing_xmcyber_data() -> None:
    """has_xmcyber_data is False when no XM Cyber enriched entity exists."""
    siemplify = _run_main([])

    siemplify.result.add_result_json.assert_called_once_with({"has_xmcyber_data": False})


def test_main_flags_present_xmcyber_data() -> None:
    """has_xmcyber_data is True alongside the alert JSON when entities are enriched."""
    entity = MagicMock()
    entity.entity_type = "HOSTNAME"
    entity.additional_properties = _entity_properties("40", "25")

    siemplify = _run_main([entity])

    (result_json,), _ = siemplify.result.add_result_json.call_args
    assert result_json["has_xmcyber_data"] is True
