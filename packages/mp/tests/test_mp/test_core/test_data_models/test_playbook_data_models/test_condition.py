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

import pytest
from mp.core.data_models.condition.condition import (
    Condition,
    BuiltCondition,
    NonBuiltCondition,
    MatchType,
)
from mp.core.data_models.condition.condition_group import (
    ConditionGroup,
    BuiltConditionGroup,
    NonBuiltConditionGroup,
    LogicalOperator,
)

BUILT_CONDITION: BuiltCondition = {
    "FieldName": "field_name",
    "Value": "value",
    "MatchType": 0,
}

NON_BUILT_CONDITION: NonBuiltCondition = {
    "field_name": "field_name",
    "value": "value",
    "match_type": "EQUAL",
}

CONDITION = Condition(
    field_name="field_name",
    value="value",
    match_type=MatchType.EQUAL,
)


class TestConditionDataModel:
    def test_from_built_with_valid_data(self):
        assert Condition.from_built(BUILT_CONDITION) == CONDITION

    def test_from_non_built_with_valid_data(self):
        assert Condition.from_non_built(NON_BUILT_CONDITION) == CONDITION

    def test_to_built(self):
        assert CONDITION.to_built() == BUILT_CONDITION

    def test_to_non_built(self):
        assert CONDITION.to_non_built() == NON_BUILT_CONDITION

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Condition.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            Condition.from_non_built({})

    def test_from_built_to_built_is_idempotent(self):
        assert Condition.from_built(BUILT_CONDITION).to_built() == BUILT_CONDITION

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert Condition.from_non_built(NON_BUILT_CONDITION).to_non_built() == NON_BUILT_CONDITION


BUILT_CONDITION_GROUP: BuiltConditionGroup = {
    "Conditions": [BUILT_CONDITION, BUILT_CONDITION],
    "LogicalOperator": 0,
}

NON_BUILT_CONDITION_GROUP: NonBuiltConditionGroup = {
    "conditions": [NON_BUILT_CONDITION, NON_BUILT_CONDITION],
    "logical_operator": "AND",
}

CONDITION_GROUP = ConditionGroup(
    conditions=[CONDITION, CONDITION],
    logical_operator=LogicalOperator.AND,
)

BUILT_CONDITION_GROUP_WITH_NONE: BuiltConditionGroup = {
    "Conditions": [],
    "LogicalOperator": 0,
}

NON_BUILT_CONDITION_GROUP_WITH_NONE: NonBuiltConditionGroup = {
    "conditions": [],
    "logical_operator": "AND",
}

CONDITION_GROUP_WITH_NONE = ConditionGroup(
    conditions=[],
    logical_operator=LogicalOperator.AND,
)


class TestConditionGroupDataModel:
    def test_from_built_with_valid_data(self):
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP) == CONDITION_GROUP

    def test_from_non_built_with_valid_data(self):
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP) == CONDITION_GROUP

    def test_to_built(self):
        assert CONDITION_GROUP.to_built() == BUILT_CONDITION_GROUP

    def test_to_non_built(self):
        assert CONDITION_GROUP.to_non_built() == NON_BUILT_CONDITION_GROUP

    def test_from_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            ConditionGroup.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self):
        with pytest.raises(ValueError):
            ConditionGroup.from_non_built({})

    def test_from_built_with_none_values(self):
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP_WITH_NONE) == CONDITION_GROUP_WITH_NONE

    def test_from_non_built_with_none_values(self):
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP_WITH_NONE) == CONDITION_GROUP_WITH_NONE

    def test_to_built_with_none_values(self):
        assert CONDITION_GROUP_WITH_NONE.to_built() == BUILT_CONDITION_GROUP_WITH_NONE

    def test_to_non_built_with_none_values(self):
        assert CONDITION_GROUP_WITH_NONE.to_non_built() == NON_BUILT_CONDITION_GROUP_WITH_NONE

    def test_from_built_to_built_is_idempotent(self):
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP).to_built() == BUILT_CONDITION_GROUP

    def test_from_non_built_to_non_built_is_idempotent(self):
        assert ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP).to_non_built() == NON_BUILT_CONDITION_GROUP
