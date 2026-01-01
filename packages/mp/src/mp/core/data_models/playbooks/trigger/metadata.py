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
from mp.core.data_models.common.condition.condition_group import Condition, LogicalOperator

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.common.condition.condition import BuiltCondition, NonBuiltCondition


class BuiltTrigger(TypedDict):
    Identifier: str
    IsEnabled: bool
    DefinitionIdentifier: str
    Type: int
    WorkflowName: str | None
    LogicalOperator: int
    Conditions: list[BuiltCondition]
    Environments: list[str]


class NonBuiltTrigger(TypedDict):
    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: str
    conditions: list[NonBuiltCondition]
    logical_operator: str
    environments: list[str]
    playbook_name: NotRequired[str | None]


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
    def _from_built(cls, _: str, built: BuiltTrigger) -> Self:  # ty:ignore[invalid-method-override]
        return cls(
            playbook_id=built["DefinitionIdentifier"],
            conditions=[Condition.from_built(c) for c in built["Conditions"]],
            logical_operator=LogicalOperator(built["LogicalOperator"]),
            environments=built["Environments"],
            playbook_name=built.get("WorkflowName"),
            identifier=built["Identifier"],
            is_enabled=built["IsEnabled"],
            type_=TriggerType(built["Type"]),
        )

    @classmethod
    def _from_non_built(cls, _: str, non_built: NonBuiltTrigger) -> Self:  # ty:ignore[invalid-method-override]
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
        )

    def to_built(self) -> BuiltTrigger:
        """Convert the Trigger to its "built" representation.

        Returns:
            A BuiltTrigger dictionary.

        """
        return BuiltTrigger(
            Identifier=self.identifier,
            IsEnabled=self.is_enabled,
            DefinitionIdentifier=self.playbook_id,
            WorkflowName=self.playbook_name,
            Type=self.type_.value,
            LogicalOperator=self.logical_operator.value,
            Conditions=[Condition.to_built(c) for c in self.conditions if c is not None],
            Environments=self.environments,
        )

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
        return non_built
