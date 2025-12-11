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

from .visibility_property import (
    BuiltIntegrationVisibilityProperty,
    IntegrationVisibilityProperty,
    NonBuiltIntegrationVisibilityProperty,
)


class BuiltFeatureTags(TypedDict):
    IntegrationVisibilityProperties: list[BuiltIntegrationVisibilityProperty]


class NonBuiltFeatureTags(TypedDict):
    integration_visibility_properties: list[NonBuiltIntegrationVisibilityProperty]


class FeatureTags(Buildable[BuiltFeatureTags, NonBuiltFeatureTags]):
    integration_visibility_properties: list[IntegrationVisibilityProperty]

    @classmethod
    def _from_built(cls, built: BuiltFeatureTags) -> Self:
        return cls(
            integration_visibility_properties=[
                IntegrationVisibilityProperty.from_built(p)
                for p in built["IntegrationVisibilityProperties"]
            ],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltFeatureTags) -> Self:
        return cls(
            integration_visibility_properties=[
                IntegrationVisibilityProperty.from_non_built(p)
                for p in non_built["integration_visibility_properties"]
            ],
        )

    def to_built(self) -> BuiltFeatureTags:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltFeatureTags(
            IntegrationVisibilityProperties=[
                p.to_built() for p in self.integration_visibility_properties
            ]
        )

    def to_non_built(self) -> NonBuiltFeatureTags:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltFeatureTags(
            integration_visibility_properties=[
                p.to_non_built() for p in self.integration_visibility_properties
            ]
        )
