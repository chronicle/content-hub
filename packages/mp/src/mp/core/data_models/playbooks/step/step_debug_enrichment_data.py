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


class BuiltStepDebugEnrichmentData(TypedDict):
    Field: str
    Value: str
    UseInPlaybook: bool
    IsCustom: bool


class NonBuiltStepDebugEnrichmentData(TypedDict):
    field: str
    value: str
    use_in_playbook: bool
    is_custom: bool


class DebugStepEnrichmentData(
    Buildable[BuiltStepDebugEnrichmentData, NonBuiltStepDebugEnrichmentData]
):
    field: str
    value: str
    use_in_playbook: bool
    is_custom: bool

    @classmethod
    def _from_built(cls, built: BuiltStepDebugEnrichmentData) -> Self:
        return cls(
            field=built["Field"],
            value=built["Value"],
            use_in_playbook=built["UseInPlaybook"],
            is_custom=built["IsCustom"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltStepDebugEnrichmentData) -> Self:
        return cls(
            field=non_built["field"],
            value=non_built["value"],
            use_in_playbook=non_built["use_in_playbook"],
            is_custom=non_built["is_custom"],
        )

    def to_built(self) -> BuiltStepDebugEnrichmentData:
        """Convert the DebugStepEnrichmentData to its "built" representation.

        Returns:
            A BuiltStepDebugEnrichmentData dictionary.

        """
        return BuiltStepDebugEnrichmentData(
            Field=self.field,
            Value=self.value,
            UseInPlaybook=self.use_in_playbook,
            IsCustom=self.is_custom,
        )

    def to_non_built(self) -> NonBuiltStepDebugEnrichmentData:
        """Convert the DebugStepEnrichmentData to its "non-built" representation.

        Returns:
            A NonBuiltStepDebugEnrichmentData dictionary.

        """
        return NonBuiltStepDebugEnrichmentData(
            field=self.field,
            value=self.value,
            use_in_playbook=self.use_in_playbook,
            is_custom=self.is_custom,
        )
