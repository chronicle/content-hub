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

from typing import Literal, Self, TypedDict

from mp.core.data_models.abc import Buildable


class BuiltIntegrationVisibilityProperty(TypedDict):
    Kind: Literal["SystemMode", "FeatureFlag"]
    Value: Literal["Nexus", "featEnableFederationSecondary"]


class NonBuiltIntegrationVisibilityProperty(TypedDict):
    kind: Literal["SystemMode", "FeatureFlag"]
    value: Literal["Nexus", "featEnableFederationSecondary"]


class IntegrationVisibilityProperty(
    Buildable[
        BuiltIntegrationVisibilityProperty,
        NonBuiltIntegrationVisibilityProperty,
    ],
):
    kind: Literal["SystemMode", "FeatureFlag"]
    value: Literal["Nexus", "featEnableFederationSecondary"]

    @classmethod
    def _from_built(cls, built: BuiltIntegrationVisibilityProperty) -> Self:
        return cls(
            kind=built["Kind"],
            value=built["Value"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltIntegrationVisibilityProperty) -> Self:
        return cls(
            kind=non_built["kind"],
            value=non_built["value"],
        )

    def to_built(self) -> BuiltIntegrationVisibilityProperty:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltIntegrationVisibilityProperty(Kind=self.kind, Value=self.value)

    def to_non_built(self) -> NonBuiltIntegrationVisibilityProperty:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
           The "non-built" representation of the object

        """
        return NonBuiltIntegrationVisibilityProperty(kind=self.kind, value=self.value)
