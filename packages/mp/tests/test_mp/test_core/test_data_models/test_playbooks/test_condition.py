# Copyright 2025 Google LLC
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

from __future__ import annotations

from typing import cast

import pytest

from mp.core.data_models.common.condition.condition import (
    BuiltCondition,
    Condition,
    NonBuiltCondition,
)
from mp.core.data_models.common.condition.condition_group import (
    BuiltConditionGroup,
    ConditionGroup,
    NonBuiltConditionGroup,
)

from .constants import (
    BUILT_CONDITION,
    BUILT_CONDITION_GROUP,
    BUILT_CONDITION_GROUP_WITH_NONE,
    CONDITION,
    CONDITION_GROUP,
    CONDITION_GROUP_WITH_NONE,
    NON_BUILT_CONDITION,
    NON_BUILT_CONDITION_GROUP,
    NON_BUILT_CONDITION_GROUP_WITH_NONE,
)


class TestConditionDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert Condition.from_built(BUILT_CONDITION) == CONDITION

    def test_from_non_built_with_valid_data(self) -> None:
        assert Condition.from_non_built(NON_BUILT_CONDITION) == CONDITION

    def test_to_built(self) -> None:
        assert CONDITION.to_built() == BUILT_CONDITION

    def test_to_non_built(self) -> None:
        assert CONDITION.to_non_built() == NON_BUILT_CONDITION

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            Condition.from_built(cast("BuiltCondition", cast("object", {})))

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            Condition.from_non_built(cast("NonBuiltCondition", cast("object", {})))

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert Condition.from_built(BUILT_CONDITION).to_built() == BUILT_CONDITION

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert Condition.from_non_built(NON_BUILT_CONDITION).to_non_built() == NON_BUILT_CONDITION

    def test_reaction_condition_enabled_and_operators_round_trip(self) -> None:
        built_reaction_cond: BuiltCondition = {
            "FieldName": "from",
            "Value": "",
            "MatchType": 10,
            "CustomOperatorName": None,
            "Enabled": True,
        }
        cond: Condition = Condition.from_built(built_reaction_cond)
        assert cond.enabled is True
        assert cond.match_type.to_string() == "equals_any"
        assert cond.to_built() == built_reaction_cond

        non_built_reaction_cond: NonBuiltCondition = cond.to_non_built()
        assert non_built_reaction_cond["enabled"] is True
        assert non_built_reaction_cond["match_type"] == "equals_any"
        assert Condition.from_non_built(non_built_reaction_cond).to_built() == built_reaction_cond

    def test_less_than_and_custom_match_types(self) -> None:
        less_than_built: BuiltCondition = {
            "FieldName": "count",
            "Value": "5",
            "MatchType": 4,
            "CustomOperatorName": None,
        }
        cond: Condition = Condition.from_built(less_than_built)
        assert cond.match_type.to_string() == "less_than"
        assert Condition.from_non_built(cond.to_non_built()).to_built() == less_than_built

        custom_built: BuiltCondition = {
            "FieldName": "status",
            "Value": "Open",
            "MatchType": 9,
            "CustomOperatorName": "CustomEq",
        }
        custom_cond: Condition = Condition.from_built(custom_built)
        assert custom_cond.match_type.to_string() == "custom"
        assert Condition.from_non_built(custom_cond.to_non_built()).to_built() == custom_built


class TestConditionGroupDataModel:
    def test_from_built_with_valid_data(self) -> None:
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP) == CONDITION_GROUP

    def test_from_non_built_with_valid_data(self) -> None:
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP) == CONDITION_GROUP

    def test_to_built(self) -> None:
        assert CONDITION_GROUP.to_built() == BUILT_CONDITION_GROUP

    def test_to_non_built(self) -> None:
        assert CONDITION_GROUP.to_non_built() == NON_BUILT_CONDITION_GROUP

    def test_from_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            ConditionGroup.from_built(cast("BuiltConditionGroup", cast("object", {})))

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # ruff:ignore[pytest-raises-too-broad]
            ConditionGroup.from_non_built(cast("NonBuiltConditionGroup", cast("object", {})))

    def test_from_built_with_none_values(self) -> None:
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP_WITH_NONE) == CONDITION_GROUP_WITH_NONE

    def test_from_non_built_with_none_values(self) -> None:
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP_WITH_NONE) == CONDITION_GROUP_WITH_NONE

    def test_to_built_with_none_values(self) -> None:
        assert CONDITION_GROUP_WITH_NONE.to_built() == BUILT_CONDITION_GROUP_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert CONDITION_GROUP_WITH_NONE.to_non_built() == NON_BUILT_CONDITION_GROUP_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP).to_built() == BUILT_CONDITION_GROUP

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP).to_non_built() == NON_BUILT_CONDITION_GROUP
