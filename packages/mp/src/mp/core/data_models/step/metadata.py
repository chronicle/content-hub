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

from typing import TYPE_CHECKING, Annotated, Self, TypedDict

import pydantic

import mp.core.data_models.abc

from .step_debug_data import BuiltStepDebugData, NonBuiltStepDebugData, StepDebugData
from .step_parameter import BuiltStepParameter, NonBuiltStepParameter, StepParameter

if TYPE_CHECKING:
    from pathlib import Path


class StepType(mp.core.data_models.abc.RepresentableEnum):
    ACTION = 0
    MULTI_CHOICE_QUESTION = 1
    PREVIOUS_ACTION = 2
    CASE_DATA_CONDITION = 3
    CONDITION = 4
    BLOCK = 5
    OUTPUT = 6
    PARALLEL_ACTIONS_CONTAINER = 7
    FOR_EACH_START_LOOP = 8
    FOR_EACH_END_LOOP = 9


class BuiltStep(TypedDict):
    Name: str
    Description: str
    Identifier: str
    OriginalStepIdentifier: str
    ParentWorkflowIdentifier: str
    ParentStepIdentifiers: list[str]
    PreviousResultCondition: str
    InstanceName: str
    IsAutomatic: bool
    IsSkippable: bool
    ActionProvider: str
    ActionName: str
    Type: int
    Integration: str
    Parameters: list[BuiltStepParameter]
    AutoSkipOnFailure: bool
    IsDebugMockData: bool
    StepDebugData: BuiltStepDebugData | None
    StartLoopStepIdentifier: str | None
    ParallelActions: list[BuiltStep]
    ParentContainerIdentifier: str | None
    IsTouchedByAi: bool


class NonBuiltStep(TypedDict):
    name: str
    description: str
    identifier: str
    original_step_id: str
    playbook_id: str
    parent_step_ids: list[str]
    previous_result_condition: str
    instance_name: str
    is_automatic: bool
    is_skippable: bool
    action_provider: str
    action_name: str
    integration: str
    type: str
    parameters: list[NonBuiltStepParameter]
    auto_skip_on_failure: bool
    is_debug_mock_data: bool
    step_debug_data: NonBuiltStepDebugData | None
    start_loop_step_id: str | None
    parent_container_id: str | None
    is_touched_by_ai: bool
    parallel_actions: list[NonBuiltStep]


class Step(mp.core.data_models.abc.ComponentMetadata):
    name: str
    description: str
    identifier: str
    original_step_id: str
    playbook_id: str
    parent_step_ids: list[str]
    previous_result_condition: str
    instance_name: str
    is_automatic: bool
    is_skippable: bool
    action_provider: str
    action_name: str
    integration: str
    type_: StepType
    parameters: list[StepParameter]
    auto_skip_on_failure: bool
    is_debug_mock_data: bool
    is_touched_by_ai: bool
    step_debug_data: StepDebugData | None = None
    start_loop_step_id: str | None = None
    parent_container_id: str | None = None
    parallel_actions: Annotated[list[Step], pydantic.Field(default_factory=list)]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        pass

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        pass

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltStep) -> Self:
        return cls(
            name=built["Name"],
            description=built["Description"],
            identifier=built["Identifier"],
            original_step_id=built["OriginalStepIdentifier"],
            playbook_id=built["ParentWorkflowIdentifier"],
            parent_step_ids=built["ParentStepIdentifiers"],
            instance_name=built["InstanceName"],
            is_automatic=built["IsAutomatic"],
            is_skippable=built["IsSkippable"],
            action_provider=built["ActionProvider"],
            parameters=[StepParameter.from_built(p) for p in built["Parameters"]],
            step_debug_data=StepDebugData.from_built(built["StepDebugData"]),
            is_debug_mock_data=built["IsDebugMockData"],
            auto_skip_on_failure=built["AutoSkipOnFailure"],
            start_loop_step_id=built.get("StartLoopStepIdentifier"),
            integration=built["Integration"],
            parent_container_id=built.get("ParentContainerIdentifier"),
            action_name=built["ActionName"],
            parallel_actions=[cls.from_built(file_name, pa) for pa in built["ParallelActions"]],
            previous_result_condition=built["PreviousResultCondition"],
            is_touched_by_ai=built["IsTouchedByAi"],
            type_=StepType(built["Type"]),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltStep) -> Self:
        return cls(
            name=non_built["name"],
            description=non_built["description"],
            identifier=non_built["identifier"],
            original_step_id=non_built["original_step_id"],
            playbook_id=non_built["playbook_id"],
            parent_step_ids=non_built["parent_step_ids"],
            instance_name=non_built["instance_name"],
            is_automatic=non_built["is_automatic"],
            is_skippable=non_built["is_skippable"],
            action_name=non_built["action_name"],
            parent_container_id=non_built.get("parent_container_id"),
            start_loop_step_id=non_built.get("start_loop_step_id"),
            step_debug_data=StepDebugData.from_non_built(non_built["step_debug_data"]),
            parallel_actions=[
                cls.from_non_built(file_name, pa) for pa in non_built["parallel_actions"]
            ],
            parameters=[StepParameter.from_non_built(p) for p in non_built["parameters"]],
            auto_skip_on_failure=non_built["auto_skip_on_failure"],
            is_debug_mock_data=non_built["is_debug_mock_data"],
            integration=non_built["integration"],
            action_provider=non_built["action_provider"],
            previous_result_condition=non_built["previous_result_condition"],
            is_touched_by_ai=non_built["is_touched_by_ai"],
            type_=StepType.from_string(non_built["type"]),
        )

    def to_built(self) -> BuiltStep:
        return BuiltStep(
            Name=self.name,
            Description=self.description,
            Identifier=self.identifier,
            OriginalStepIdentifier=self.original_step_id,
            ParentWorkflowIdentifier=self.playbook_id,
            ParentStepIdentifiers=self.parent_step_ids,
            InstanceName=self.instance_name,
            IsAutomatic=self.is_automatic,
            IsSkippable=self.is_skippable,
            StepDebugData=(
                self.step_debug_data.to_built() if self.step_debug_data is not None else None
            ),
            StartLoopStepIdentifier=self.start_loop_step_id,
            ActionName=self.action_name,
            Parameters=[p.to_built() for p in self.parameters],
            Integration=self.integration,
            ActionProvider=self.action_provider,
            IsDebugMockData=self.is_debug_mock_data,
            AutoSkipOnFailure=self.auto_skip_on_failure,
            ParentContainerIdentifier=self.parent_container_id,
            ParallelActions=[p.to_built() for p in self.parallel_actions],
            IsTouchedByAi=self.is_touched_by_ai,
            Type=self.type_.value,
            PreviousResultCondition=self.previous_result_condition,
        )

    def to_non_built(self) -> NonBuiltStep:
        return NonBuiltStep(
            name=self.name,
            description=self.description,
            identifier=self.identifier,
            original_step_id=self.original_step_id,
            playbook_id=self.playbook_id,
            parent_step_ids=self.parent_step_ids,
            instance_name=self.instance_name,
            is_automatic=self.is_automatic,
            is_skippable=self.is_skippable,
            action_provider=self.action_provider,
            step_debug_data=self.step_debug_data,
            start_loop_step_id=self.start_loop_step_id,
            parameters=[p.to_non_built() for p in self.parameters],
            action_name=self.action_name,
            parallel_actions=[p.to_non_built() for p in self.parallel_actions],
            integration=self.integration,
            parent_container_id=self.parent_container_id,
            is_touched_by_ai=self.is_touched_by_ai,
            is_debug_mock_data=self.is_debug_mock_data,
            auto_skip_on_failure=self.auto_skip_on_failure,
            previous_result_condition=self.previous_result_condition,
            type=self.type_.to_string(),
        )
