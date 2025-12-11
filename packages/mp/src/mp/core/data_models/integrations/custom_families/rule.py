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

from mp.core.data_models.abc import Buildable


class BuiltCustomFamilyRule(TypedDict):
    PrimarySource: str
    SecondarySource: str | None
    ThirdSource: str | None
    FourthSource: str | None
    RelationType: str
    PrimaryDestination: str
    SecondaryDestination: str | None
    ThirdDestination: str | None
    FourthDestination: str | None
    VisualFamily: str


class NonBuiltCustomFamilyRule(TypedDict):
    primary_source: str
    secondary_source: str | None
    third_source: str | None
    fourth_source: str | None
    relation_type: str
    primary_destination: str
    secondary_destination: str | None
    third_destination: str | None
    fourth_destination: str | None
    visual_family: str


class CustomFamilyRule(Buildable[BuiltCustomFamilyRule, NonBuiltCustomFamilyRule]):
    primary_source: str
    secondary_source: str | None
    third_source: str | None
    fourth_source: str | None
    relation_type: str
    primary_destination: str
    secondary_destination: str | None
    third_destination: str | None
    fourth_destination: str | None
    visual_family: str

    @classmethod
    def _from_built(cls, built: BuiltCustomFamilyRule) -> Self:
        return cls(
            primary_source=built["PrimarySource"],
            secondary_source=built["SecondarySource"],
            third_source=built["ThirdSource"],
            fourth_source=built["FourthSource"],
            relation_type=built["RelationType"],
            primary_destination=built["PrimaryDestination"],
            secondary_destination=built["SecondaryDestination"],
            third_destination=built["ThirdDestination"],
            fourth_destination=built["FourthDestination"],
            visual_family=built["VisualFamily"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltCustomFamilyRule) -> Self:
        return cls(
            primary_source=non_built["primary_source"],
            secondary_source=non_built["secondary_source"],
            third_source=non_built["third_source"],
            fourth_source=non_built["fourth_source"],
            relation_type=non_built["relation_type"],
            primary_destination=non_built["primary_destination"],
            secondary_destination=non_built["secondary_destination"],
            third_destination=non_built["third_destination"],
            fourth_destination=non_built["fourth_destination"],
            visual_family=non_built["visual_family"],
        )

    def to_built(self) -> BuiltCustomFamilyRule:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "non-built" representation of the object.

        """
        return BuiltCustomFamilyRule(
            PrimarySource=self.primary_source,
            SecondarySource=self.secondary_source,
            ThirdSource=self.third_source,
            FourthSource=self.fourth_source,
            RelationType=self.relation_type,
            PrimaryDestination=self.primary_destination,
            SecondaryDestination=self.secondary_destination,
            ThirdDestination=self.third_destination,
            FourthDestination=self.fourth_destination,
            VisualFamily=self.visual_family,
        )

    def to_non_built(self) -> NonBuiltCustomFamilyRule:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "built" representation of the object

        """
        return NonBuiltCustomFamilyRule(
            primary_source=self.primary_source,
            secondary_source=self.secondary_source,
            third_source=self.third_source,
            fourth_source=self.fourth_source,
            relation_type=self.relation_type,
            primary_destination=self.primary_destination,
            secondary_destination=self.secondary_destination,
            third_destination=self.third_destination,
            fourth_destination=self.fourth_destination,
            visual_family=self.visual_family,
        )
