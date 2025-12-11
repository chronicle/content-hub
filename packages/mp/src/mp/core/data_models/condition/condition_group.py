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

from typing import Self, TypedDict

from mp.core.data_models.abc import Buildable, RepresentableEnum

from .condition import BuiltCondition, Condition, NonBuiltCondition


class LogicalOperator(RepresentableEnum):
    AND = 0
    OR = 1


class BuiltConditionGroup(TypedDict):
    Conditions: list[BuiltCondition]
    LogicalOperator: int


class NonBuiltConditionGroup(TypedDict):
    conditions: list[NonBuiltCondition]
    logical_operator: str


class ConditionGroup(Buildable[BuiltConditionGroup, NonBuiltConditionGroup]):
    conditions: list[Condition]
    logical_operator: LogicalOperator

    @classmethod
    def _from_built(cls, built: BuiltConditionGroup) -> Self:
        return cls(
            conditions=[Condition.from_built(condition) for condition in built["Conditions"]],
            logical_operator=LogicalOperator(built["LogicalOperator"]),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltConditionGroup) -> Self:
        return cls(
            conditions=[
                Condition.from_non_built(condition) for condition in non_built["conditions"]
            ],
            logical_operator=LogicalOperator.from_string(non_built["logical_operator"]),
        )

    def to_built(self) -> BuiltConditionGroup:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltConditionGroup(
            Conditions=[condition.to_built() for condition in self.conditions],
            LogicalOperator=self.logical_operator.value,
        )

    def to_non_built(self) -> NonBuiltConditionGroup:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltConditionGroup(
            conditions=[condition.to_non_built() for condition in self.conditions],
            logical_operator=self.logical_operator.to_string(),
        )
