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
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import mp.core.constants
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum, SingularComponentMetadata
from mp.core.data_models.common.condition.condition_group import (
    BuiltConditionGroup,
    Condition,
    ConditionGroup,
    LogicalOperator,
    NonBuiltConditionGroup,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.common.condition.condition import BuiltCondition, NonBuiltCondition

UNSPECIFIED_EXECUTION_MODE_API_VALUES: frozenset[str] = frozenset({
    "workflow_trigger_execution_mode_unspecified",
    "trigger_execution_mode_unspecified",
    "execution_mode_unspecified",
})


class BuiltTrigger(TypedDict):
    Identifier: str
    IsEnabled: bool
    DefinitionIdentifier: str
    Type: int
    WorkflowName: str | None
    LogicalOperator: int
    Conditions: list[BuiltCondition]
    Environments: list[str]
    ExecutionMode: NotRequired[int | str | None]
    ReactionLogicalOperator: NotRequired[int | str | None]
    ReactionConditions: NotRequired[list[BuiltConditionGroup] | None]
    MaxReactionDepth: NotRequired[int | None]


class NonBuiltTrigger(TypedDict):
    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: str
    conditions: list[NonBuiltCondition]
    logical_operator: str
    environments: list[str]
    playbook_name: NotRequired[str | None]
    execution_mode: NotRequired[str | None]
    reaction_logical_operator: NotRequired[str | None]
    reaction_conditions: NotRequired[list[NonBuiltConditionGroup] | None]
    max_reaction_depth: NotRequired[int | None]


class TriggerType(RepresentableEnum):
    """Represents the type of a trigger."""

    VENDOR_NAME = 0
    TAG_NAME = 1
    RULE_NAME = 2
    PRODUCT_NAME = 3
    NETWORK_NAME = 4
    ENTITY_DETAILS = 5
    RELATION_DETAILS = 6
    TRACKING_LIST = 7
    ALL = 8
    ALERT_TRIGGER_VALUE = 9
    CASE_DATA = 10
    GET_INPUTS = 11
    CASE_ASSIGNEE_CHANGED = 12
    ENTITY_ADDED = 13
    ALERT_PRIORITY_CHANGED = 14
    ALERT_CUSTOM_FIELD_CHANGED = 15
    CASE_CUSTOM_FIELD_CHANGED = 16
    CASE_STAGE_CHANGED = 17
    CASE_PRIORITY_CHANGED = 18
    CASE_TAG_ADDED = 19
    CASE_COMMENT_ADDED = 20


class TriggerExecutionMode(RepresentableEnum):
    """Represents the execution mode when a previous trigger run is active."""

    UNSPECIFIED = 0
    RESTART = 1
    QUEUED = 2


class Trigger(SingularComponentMetadata[BuiltTrigger, NonBuiltTrigger]):
    """Represents a trigger for a playbook."""

    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: TriggerType
    conditions: list[Condition]
    logical_operator: LogicalOperator
    environments: list[str]
    playbook_name: str | None = None
    execution_mode: TriggerExecutionMode | None = None
    reaction_logical_operator: LogicalOperator | None = None
    reaction_conditions: list[ConditionGroup] | None = None
    max_reaction_depth: int | None = None

    @classmethod
    def from_built_path(cls, path: Path) -> Self:
        """Create a list of Trigger objects from a built playbook path.

        Args:
            path: The path to the built playbook.

        Returns:
            A list of Trigger objects.

        Raises:
            ValueError: If the file at `path` fails to load or parse as JSON.

        """
        built_playbook: str = path.read_text(encoding="utf-8")
        try:
            full_playbook = json.loads(built_playbook)
            built_trigger: list[BuiltTrigger] = full_playbook["Definition"]["Triggers"]
            return cls._from_built("", built_trigger[0])
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {path}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e

    @classmethod
    def from_non_built_path(cls, path: Path) -> Self:
        """Create a list of Trigger objects from a non-built playbook path.

        Args:
            path: The path to the non-built playbook directory.

        Returns:
            A list of Trigger objects.

        """
        trigger_path: Path = path / mp.core.constants.TRIGGER_FILE_NAME
        return cls._from_non_built_path(trigger_path)

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltTrigger) -> Self:  # ruff:ignore[unused-class-method-argument]
        raw_reaction_conds: list[BuiltConditionGroup] | None = built.get("ReactionConditions")
        return cls(
            playbook_id=built["DefinitionIdentifier"],
            conditions=[Condition.from_built(c) for c in built["Conditions"]],
            logical_operator=LogicalOperator(built["LogicalOperator"]),
            environments=built["Environments"],
            playbook_name=built.get("WorkflowName"),
            identifier=built["Identifier"],
            is_enabled=built["IsEnabled"],
            type_=TriggerType(built["Type"]),
            execution_mode=TriggerExecutionMode.parse_optional(
                built.get("ExecutionMode"),
                aliases=_EXECUTION_MODE_ALIASES,
            ),
            reaction_logical_operator=LogicalOperator.parse_optional(built.get("ReactionLogicalOperator")),
            reaction_conditions=(
                [
                    ConditionGroup.from_built(condition_group)
                    for condition_group in raw_reaction_conds
                    if condition_group is not None
                ]
                if raw_reaction_conds is not None
                else None
            ),
            max_reaction_depth=built.get("MaxReactionDepth"),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltTrigger) -> Self:  # ruff:ignore[unused-class-method-argument]
        raw_reaction_conds: list[NonBuiltConditionGroup] | None = non_built.get("reaction_conditions")
        return cls(
            identifier=non_built["identifier"],
            is_enabled=non_built["is_enabled"],
            conditions=([
                Condition.from_non_built(non_built_cond)
                for non_built_cond in non_built["conditions"]
                if non_built_cond is not None
            ]),
            logical_operator=LogicalOperator.from_string(non_built["logical_operator"]),
            environments=non_built["environments"],
            playbook_id=non_built["playbook_id"],
            playbook_name=non_built["playbook_name"],
            type_=TriggerType.from_string(non_built["type_"]),
            execution_mode=TriggerExecutionMode.parse_optional(
                non_built.get("execution_mode"),
                aliases=_EXECUTION_MODE_ALIASES,
            ),
            reaction_logical_operator=LogicalOperator.parse_optional(non_built.get("reaction_logical_operator")),
            reaction_conditions=(
                [
                    ConditionGroup.from_non_built(condition_group)
                    for condition_group in raw_reaction_conds
                    if condition_group is not None
                ]
                if raw_reaction_conds is not None
                else None
            ),
            max_reaction_depth=non_built.get("max_reaction_depth"),
        )

    def to_built(self) -> BuiltTrigger:
        """Convert the Trigger to its "built" representation.

        Returns:
            A BuiltTrigger dictionary.

        """
        built: BuiltTrigger = BuiltTrigger(
            Identifier=self.identifier,
            IsEnabled=self.is_enabled,
            DefinitionIdentifier=self.playbook_id,
            WorkflowName=self.playbook_name,
            Type=self.type_.value,
            LogicalOperator=self.logical_operator.value,
            Conditions=[Condition.to_built(c) for c in self.conditions if c is not None],
            Environments=self.environments,
        )
        if self.execution_mode is not None:
            built["ExecutionMode"] = self.execution_mode.value
        if self.reaction_logical_operator is not None:
            built["ReactionLogicalOperator"] = self.reaction_logical_operator.value
        if self.reaction_conditions is not None:
            built["ReactionConditions"] = [
                condition_group.to_built()
                for condition_group in self.reaction_conditions
                if condition_group is not None
            ]
        if self.max_reaction_depth is not None:
            built["MaxReactionDepth"] = self.max_reaction_depth
        return built

    def to_non_built(self) -> NonBuiltTrigger:
        """Convert the Trigger to its "non-built" representation.

        Returns:
            A NonBuiltTrigger dictionary.

        """
        non_built: NonBuiltTrigger = NonBuiltTrigger(
            identifier=self.identifier,
            is_enabled=self.is_enabled,
            playbook_id=self.playbook_id,
            type_=self.type_.to_string(),
            conditions=[Condition.to_non_built(c) for c in self.conditions if c is not None],
            logical_operator=self.logical_operator.to_string(),
            environments=self.environments,
            playbook_name=self.playbook_name,
        )
        if self.execution_mode is not None:
            non_built["execution_mode"] = self.execution_mode.to_string()
        if self.reaction_logical_operator is not None:
            non_built["reaction_logical_operator"] = self.reaction_logical_operator.to_string()
        if self.reaction_conditions is not None:
            non_built["reaction_conditions"] = [
                condition_group.to_non_built()
                for condition_group in self.reaction_conditions
                if condition_group is not None
            ]
        if self.max_reaction_depth is not None:
            non_built["max_reaction_depth"] = self.max_reaction_depth
        return non_built


_EXECUTION_MODE_ALIASES: dict[str, TriggerExecutionMode] = dict.fromkeys(
    UNSPECIFIED_EXECUTION_MODE_API_VALUES,
    TriggerExecutionMode.UNSPECIFIED,
)
