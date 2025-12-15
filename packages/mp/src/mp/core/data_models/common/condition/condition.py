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


class MatchType(RepresentableEnum):
    EQUAL = 0
    CONTAINS = 1
    STARTS_WITH = 2
    GREATER_THAN = 3
    LESS_THAN = 3
    NOT_EQUAL = 5
    NOT_CONTAINS = 6
    IS_EMPTY = 7
    IS_NOT_EMPTY = 8


class BuiltCondition(TypedDict):
    FieldName: str
    Value: str | None
    MatchType: int
    CustomOperatorName: str | None


class NonBuiltCondition(TypedDict):
    field_name: str
    value: str | None
    match_type: str
    custom_operator_name: str | None


class Condition(Buildable[BuiltCondition, NonBuiltCondition]):
    field_name: str
    value: str | None
    match_type: MatchType
    custom_operator_name: str | None

    @classmethod
    def _from_built(cls, built: BuiltCondition) -> Self:
        return cls(
            field_name=built["FieldName"],
            value=built["Value"],
            match_type=MatchType(built["MatchType"]),
            custom_operator_name=built.get("CustomOperatorName"),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltCondition) -> Self:
        return cls(
            field_name=non_built["field_name"],
            value=non_built["value"],
            match_type=MatchType.from_string(non_built["match_type"]),
            custom_operator_name=non_built.get("custom_operator_name"),
        )

    def to_built(self) -> BuiltCondition:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltCondition(
            FieldName=self.field_name,
            Value=self.value,
            MatchType=self.match_type.value,
            CustomOperatorName=self.custom_operator_name,
        )

    def to_non_built(self) -> NonBuiltCondition:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltCondition(
            field_name=self.field_name,
            value=self.value,
            match_type=self.match_type.to_string(),
            custom_operator_name=self.custom_operator_name,
        )
