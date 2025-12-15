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

from mp.core.data_models.common.condition.condition import (
    Condition,
)
from mp.core.data_models.common.condition.condition_group import (
    ConditionGroup,
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
        with pytest.raises(ValueError):  # noqa: PT011
            Condition.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            Condition.from_non_built({})

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert Condition.from_built(BUILT_CONDITION).to_built() == BUILT_CONDITION

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert Condition.from_non_built(NON_BUILT_CONDITION).to_non_built() == NON_BUILT_CONDITION


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
        with pytest.raises(ValueError):  # noqa: PT011
            ConditionGroup.from_built({})

    def test_from_non_built_with_invalid_data_raises_error(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            ConditionGroup.from_non_built({})

    def test_from_built_with_none_values(self) -> None:
        assert (
            ConditionGroup.from_built(BUILT_CONDITION_GROUP_WITH_NONE) == CONDITION_GROUP_WITH_NONE
        )

    def test_from_non_built_with_none_values(self) -> None:
        assert (
            ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP_WITH_NONE)
            == CONDITION_GROUP_WITH_NONE
        )

    def test_to_built_with_none_values(self) -> None:
        assert CONDITION_GROUP_WITH_NONE.to_built() == BUILT_CONDITION_GROUP_WITH_NONE

    def test_to_non_built_with_none_values(self) -> None:
        assert CONDITION_GROUP_WITH_NONE.to_non_built() == NON_BUILT_CONDITION_GROUP_WITH_NONE

    def test_from_built_to_built_is_idempotent(self) -> None:
        assert ConditionGroup.from_built(BUILT_CONDITION_GROUP).to_built() == BUILT_CONDITION_GROUP

    def test_from_non_built_to_non_built_is_idempotent(self) -> None:
        assert (
            ConditionGroup.from_non_built(NON_BUILT_CONDITION_GROUP).to_non_built()
            == NON_BUILT_CONDITION_GROUP
        )
