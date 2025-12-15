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

import json
from typing import NotRequired, Self, TypedDict

import mp.core.data_models.abc
from mp.core.custom_types import JsonString  # noqa: TC001

from .step_debug_enrichment_data import (
    BuiltStepDebugEnrichmentData,
    DebugStepEnrichmentData,
    NonBuiltStepDebugEnrichmentData,
)


class BuiltStepDebugData(TypedDict):
    CreationTimeUnixTimeInMs: int
    ModificationTimeUnixTimeInMs: int
    OriginalWorkflowIdentifier: str
    OriginalStepIdentifier: str
    ResultValue: str
    ResultJson: JsonString
    ScopeEntitiesEnrichmentData: list[BuiltStepDebugEnrichmentData]
    ScopeEntitiesEnrichmentDataJson: str
    TenantId: NotRequired[str | None]


class NonBuiltStepDebugData(TypedDict):
    step_id: str
    playbook_id: str
    creation_time: int
    modification_time: int
    result_value: str
    result_json: str
    scope_entities_enrichment_data: list[NonBuiltStepDebugEnrichmentData]
    tenant_id: NotRequired[str | None]


class StepDebugData(
    mp.core.data_models.abc.Buildable[BuiltStepDebugData, NonBuiltStepDebugData],
):
    step_id: str
    playbook_id: str
    creation_time: int
    modification_time: int
    result_value: str | None
    result_json: JsonString | None
    scope_entities_enrichment_data: list[DebugStepEnrichmentData]
    tenant_id: str | None = None

    @classmethod
    def _from_built(cls, built: BuiltStepDebugData) -> Self:
        """Create the obj from a built action param dict.

        Args:
            built: the built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            step_id=built["OriginalStepIdentifier"],
            playbook_id=built["OriginalWorkflowIdentifier"],
            creation_time=built["CreationTimeUnixTimeInMs"],
            modification_time=built["ModificationTimeUnixTimeInMs"],
            result_value=built["ResultValue"],
            result_json=built["ResultJson"],
            scope_entities_enrichment_data=(
                [
                    DebugStepEnrichmentData.from_built(d)
                    for d in built["ScopeEntitiesEnrichmentData"]
                ]
                if built.get("ScopeEntitiesEnrichmentData")
                else []
            ),
            tenant_id=built.get("TenantId"),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltStepDebugData) -> Self:
        """Create the obj from a non-built action param dict.

        Args:
            non_built: the non-built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            step_id=non_built["step_id"],
            playbook_id=non_built["playbook_id"],
            creation_time=non_built["creation_time"],
            modification_time=non_built["modification_time"],
            result_value=non_built["result_value"],
            result_json=non_built["result_json"],
            scope_entities_enrichment_data=([
                DebugStepEnrichmentData.from_non_built(en)
                for en in non_built["scope_entities_enrichment_data"]
            ]),
            tenant_id=non_built.get("tenant_id"),
        )

    def to_built(self) -> BuiltStepDebugData:
        """Convert the StepDebugData to its "built" representation.

        Returns:
            A BuiltStepDebugData dictionary.

        """
        enrichment_data: list[BuiltStepDebugEnrichmentData] = [
            e.to_built() for e in self.scope_entities_enrichment_data
        ]
        res: BuiltStepDebugData = BuiltStepDebugData(
            CreationTimeUnixTimeInMs=self.creation_time,
            ModificationTimeUnixTimeInMs=self.modification_time,
            OriginalWorkflowIdentifier=self.playbook_id,
            OriginalStepIdentifier=self.step_id,
            ResultValue=self.result_value,
            ResultJson=self.result_json,
            ScopeEntitiesEnrichmentData=enrichment_data,
            ScopeEntitiesEnrichmentDataJson=json.dumps(enrichment_data),
        )
        if self.tenant_id is not None:
            res["TenantId"] = self.tenant_id
        return res

    def to_non_built(self) -> NonBuiltStepDebugData:
        """Convert the StepDebugData to its "non-built" representation.

        Returns:
            A NonBuiltStepDebugData dictionary.

        """
        non_built: NonBuiltStepDebugData = NonBuiltStepDebugData(
            step_id=self.step_id,
            playbook_id=self.playbook_id,
            creation_time=self.creation_time,
            modification_time=self.modification_time,
            result_value=self.result_value,
            result_json=self.result_json,
            scope_entities_enrichment_data=[
                e.to_non_built() for e in self.scope_entities_enrichment_data
            ],
        )
        if self.tenant_id is not None:
            non_built["tenant_id"] = self.tenant_id
        return non_built
