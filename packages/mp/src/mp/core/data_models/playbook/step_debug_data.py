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

from typing import Annotated, Any, NotRequired, Self, TypedDict

import pydantic

import mp.core.data_models.abc
import mp.core.utils

from .step_debug_enrichment_data import BuiltStepDebugEnrichmentData, DebugStepEnrichmentData


class BuiltStepDebugData(TypedDict):
    OriginalStepIdentifier: str
    OriginalWorkflowIdentifier: str
    ModificationTimeUnixTimeInMs: int
    CreationTimeUnixTimeInMs: int
    ResultValue: str
    ResultJson: str
    ScopeEntitiesEnrichmentDataJson: str
    TenantId: NotRequired[str | None]


class NonBuiltStepDebugData(TypedDict):
    step_id: str
    playbook_id: str
    creation_time: int
    modification_time: int
    result_value: str
    result_json: pydantic.Json
    scope_entities_enrichment_data: BuiltStepDebugEnrichmentData
    tenant_id: str | None


class StepDebugData(
    mp.core.data_models.abc.Buildable[BuiltStepDebugData, NonBuiltStepDebugData],
):
    step_id: str
    playbook_id: str
    creation_time: int
    modification_time: int
    result_value: str
    result_json: pydantic.Json[Any]
    scope_entities_enrichment_data: Annotated[DebugStepEnrichmentData, pydantic.PlainValidator()]
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
            scope_entities_enrichment_data=DebugStepEnrichmentData.model_validate_json(
                built["ScopeEntitiesEnrichmentDataJson"]
            ),
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
            scope_entities_enrichment_data=DebugStepEnrichmentData.model_validate(
                non_built["scope_entities_enrichment_data"]
            ),
            tenant_id=non_built.get("tenant_id"),
        )

    def to_built(self) -> BuiltStepDebugData:
        """Create a built action param dict.

        Returns:
            A built version of the action parameter dict

        """
        return BuiltStepDebugData(
            OriginalStepIdentifier=self.step_id,
            OriginalWorkflowIdentifier=self.playbook_id,
            ModificationTimeUnixTimeInMs=self.modification_time,
            CreationTimeUnixTimeInMs=self.creation_time,
            ResultValue=self.result_value,
            ResultJson=self.result_json,
            ScopeEntitiesEnrichmentDataJson=self.scope_entities_enrichment_data.model_dump_json(),
            TenantId=self.tenant_id,
        )

    def to_non_built(self) -> NonBuiltStepDebugData:
        """Create a non-built action param dict.

        Returns:
            A non-built version of the action parameter dict

        """
        non_built: NonBuiltStepDebugData = NonBuiltStepDebugData(
            step_id=self.step_id,
            playbook_id=self.playbook_id,
            creation_time=self.creation_time,
            modification_time=self.modification_time,
            result_value=self.result_value,
            result_json=self.result_json,
            scope_entities_enrichment_data=self.scope_entities_enrichment_data.model_dump(),
            tenant_id=self.tenant_id,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
