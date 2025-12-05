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
from typing import TYPE_CHECKING, Annotated, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils

from .step_debug_data import BuiltStepDebugData, NonBuiltStepDebugData, StepDebugData
from .step_parameter import BuiltStepParameter, NonBuiltStepParameter, StepParameter

if TYPE_CHECKING:
    from pathlib import Path


class BuiltStep(TypedDict):
    Identifier: str
    OriginalStepIdentifier: str
    ParentWorkflowIdentifier: str
    ParentStepIdentifiers: list[str]
    ParentStepIdentifier: str
    PreviousResultCondition: str
    InstanceName: str
    IsAutomatic: bool
    Name: str
    IsSkippable: bool
    Description: str
    ActionProvider: str
    ActionName: str
    Type: int
    Integration: str | None
    Parameters: list[BuiltStepParameter]
    AutoSkipOnFailure: bool
    IsDebugMockData: bool
    StepDebugData: BuiltStepDebugData | None
    ParentStepContainerId: str | None
    IsTouchedByAi: bool
    StartLoopStepIdentifier: str | None
    ParallelActions: list[BuiltStep]


class NonBuiltStep(TypedDict):
    name: str
    description: str
    identifier: str
    original_step_id: str
    playbook_id: str
    parent_step_ids: list[str]
    parent_step_id: str
    previous_result_condition: str
    instance_name: str
    is_automatic: bool
    is_skippable: bool
    action_provider: str
    action_name: str
    integration: str | None
    type: str
    parameters: list[NonBuiltStepParameter]
    auto_skip_on_failure: bool
    is_debug_mock_data: bool
    step_debug_data: NonBuiltStepDebugData | None
    start_loop_step_id: str | None
    parent_container_id: str | None
    is_touched_by_ai: bool
    parallel_actions: list[NonBuiltStep]


class StepType(mp.core.data_models.abc.RepresentableEnum):
    """Represents the type of a step."""

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


class Step(mp.core.data_models.abc.ComponentMetadata):
    """Represents a step in a playbook."""

    name: str
    description: str
    identifier: str
    original_step_id: str
    playbook_id: str
    parent_step_ids: list[str]
    parent_step_id: str
    previous_result_condition: str | None = None
    instance_name: str
    is_automatic: bool
    is_skippable: bool
    action_provider: str
    action_name: str
    integration: str | None = None
    type_: StepType
    parameters: list[StepParameter]
    auto_skip_on_failure: bool
    is_debug_mock_data: bool
    step_debug_data: StepDebugData | None = None
    is_touched_by_ai: bool
    start_loop_step_id: str | None = None
    parent_container_id: str | None = None
    parallel_actions: Annotated[
        list[Step],
        pydantic.Field(max_length=mp.core.constants.MAX_STEP_PARALLEL_ACTIONS),
        pydantic.Field(default_factory=list),
    ]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create a list of Step objects from a built playbook path.

        Args:
            path: The path to the built playbook.

        Returns:
            A list of Step objects.

        Raises:
            ValueError: If the file at `path` fails to load or parse as JSON.

        """
        if not path.exists():
            return []
        built_playbook: str = path.read_text(encoding="utf-8")
        try:
            full_playbook = json.loads(built_playbook)
            built_steps: list[BuiltStep] = full_playbook["Definition"]["Steps"]
            return [cls._from_built("", step) for step in built_steps]
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {path}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create a list of Step objects from a non-built playbook path.

        Args:
            path: The path to the non-built playbook directory.

        Returns:
            A list of Step objects.

        """
        step_folder_path: Path = path / mp.core.constants.STEPS_DIR
        if not step_folder_path.exists():
            return []

        return [
            cls._from_non_built_path(step_path)
            for step_path in step_folder_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltStep) -> Self:
        return cls(
            name=built["Name"],
            description=built["Description"],
            identifier=built["Identifier"],
            original_step_id=built["OriginalStepIdentifier"],
            playbook_id=built["ParentWorkflowIdentifier"],
            parent_step_ids=built["ParentStepIdentifiers"],
            parent_step_id=built["ParentStepIdentifier"],
            instance_name=built["InstanceName"],
            is_automatic=built["IsAutomatic"],
            is_skippable=built["IsSkippable"],
            action_provider=built["ActionProvider"],
            parameters=[StepParameter.from_built(p) for p in built["Parameters"]],
            is_debug_mock_data=built["IsDebugMockData"],
            step_debug_data=(
                StepDebugData.from_built(built["StepDebugData"])
                if built.get("StepDebugData")
                else None
            ),
            auto_skip_on_failure=built["AutoSkipOnFailure"],
            start_loop_step_id=built.get("StartLoopStepIdentifier"),
            integration=built["Integration"],
            parent_container_id=built.get("ParentStepContainerId"),
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
            parent_step_id=non_built["parent_step_id"],
            instance_name=non_built["instance_name"],
            is_automatic=non_built["is_automatic"],
            is_skippable=non_built["is_skippable"],
            action_name=non_built["action_name"],
            parent_container_id=non_built.get("parent_container_id"),
            start_loop_step_id=non_built.get("start_loop_step_id"),
            parallel_actions=[
                cls.from_non_built(file_name, pa) for pa in non_built["parallel_actions"]
            ],
            parameters=[StepParameter.from_non_built(p) for p in non_built["parameters"]],
            auto_skip_on_failure=non_built["auto_skip_on_failure"],
            is_debug_mock_data=non_built["is_debug_mock_data"],
            step_debug_data=(
                StepDebugData.from_non_built(non_built["step_debug_data"])
                if non_built.get("step_debug_data")
                else None
            ),
            integration=non_built["integration"],
            action_provider=non_built["action_provider"],
            previous_result_condition=non_built["previous_result_condition"],
            is_touched_by_ai=non_built["is_touched_by_ai"],
            type_=StepType.from_string(non_built["type"]),
        )

    def to_built(self) -> BuiltStep:
        """Convert the Step to its "built" representation.

        Returns:
            A BuiltStep dictionary.

        """
        return BuiltStep(
            Identifier=self.identifier,
            OriginalStepIdentifier=self.original_step_id,
            ParentWorkflowIdentifier=self.playbook_id,
            ParentStepIdentifiers=self.parent_step_ids,
            ParentStepIdentifier=self.parent_step_id,
            PreviousResultCondition=self.previous_result_condition,
            InstanceName=self.instance_name,
            IsAutomatic=self.is_automatic,
            Name=self.name,
            IsSkippable=self.is_skippable,
            Description=self.description,
            ActionProvider=self.action_provider,
            ActionName=self.action_name,
            Type=self.type_.value,
            Integration=self.integration,
            Parameters=[p.to_built() for p in self.parameters],
            AutoSkipOnFailure=self.auto_skip_on_failure,
            IsDebugMockData=self.is_debug_mock_data,
            StepDebugData=(
                self.step_debug_data.to_built() if self.step_debug_data is not None else None
            ),
            ParentStepContainerId=self.parent_container_id,
            IsTouchedByAi=self.is_touched_by_ai,
            StartLoopStepIdentifier=self.start_loop_step_id,
            ParallelActions=[p.to_built() for p in self.parallel_actions],
        )

    def to_non_built(self) -> NonBuiltStep:
        """Convert the Step to its "non-built" representation.

        Returns:
            A NonBuiltStep dictionary.

        """
        return NonBuiltStep(
            name=self.name,
            description=self.description,
            identifier=self.identifier,
            original_step_id=self.original_step_id,
            playbook_id=self.playbook_id,
            parent_step_ids=self.parent_step_ids,
            parent_step_id=self.parent_step_id,
            instance_name=self.instance_name,
            is_automatic=self.is_automatic,
            is_skippable=self.is_skippable,
            action_provider=self.action_provider,
            start_loop_step_id=self.start_loop_step_id,
            parameters=[p.to_non_built() for p in self.parameters],
            action_name=self.action_name,
            parallel_actions=[p.to_non_built() for p in self.parallel_actions],
            integration=self.integration,
            parent_container_id=self.parent_container_id,
            is_touched_by_ai=self.is_touched_by_ai,
            is_debug_mock_data=self.is_debug_mock_data,
            step_debug_data=(
                self.step_debug_data.to_non_built() if self.step_debug_data is not None else None
            ),
            auto_skip_on_failure=self.auto_skip_on_failure,
            previous_result_condition=self.previous_result_condition,
            type=self.type_.to_string(),
        )
