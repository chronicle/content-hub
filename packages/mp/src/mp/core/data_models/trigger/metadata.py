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

from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum
from mp.core.data_models.condition import Condition, LogicalOperator

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.condition import BuiltCondition, NonBuiltCondition


class TriggerType(RepresentableEnum):
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


class BuiltTrigger(TypedDict):
    Identifier: str
    IsEnabled: bool
    DefinitionIdentifier: str
    Type: int
    LogicalOperator: int
    Conditions: list[BuiltCondition]
    Environments: list[str]
    WorkflowName: str | None


class NonBuiltTrigger(TypedDict):
    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: str
    conditions: list[NonBuiltCondition]
    logical_operator: str
    environments: list[str]
    playbook_name: NotRequired[str | None]


class Trigger(mp.core.data_models.abc.SequentialMetadata):
    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: TriggerType
    conditions: list[Condition]
    logical_operator: LogicalOperator
    environments: list[str]
    playbook_name: str | None = None

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        rn_path: Path = path / mp.core.constants.TRIGGERS_FILE_NAME
        if not rn_path.exists():
            return []

        return cls._from_built_path(rn_path)

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        rn_path: Path = path / mp.core.constants.TRIGGERS_FILE_NAME
        if not rn_path.exists():
            return []

        return cls._from_non_built_path(rn_path)

    @classmethod
    def _from_built(cls, built: BuiltTrigger) -> Self:
        return cls(
            playbook_id=built["DefinitionIdentifier"],
            conditions=Condition.from_built(built["Conditions"]),
            logical_operator=LogicalOperator(built["LogicalOperator"]),
            environments=built["Environments"],
            playbook_name=built.get("WorkflowName"),
            identifier=built["Identifier"],
            is_enabled=built["IsEnabled"],
            type_=TriggerType(built["Type"]),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltTrigger) -> Self:
        return cls(
            is_enabled=non_built["is_enabled"],
            identifier=non_built["identifier"],
            conditions=Condition.from_non_built(non_built["conditions"]),
            logical_operator=LogicalOperator.from_string(non_built["logical_operator"]),
            environments=non_built["environments"],
            playbook_id=non_built["playbook_id"],
            playbook_name=non_built["playbook_name"],
            type_=TriggerType.from_string(non_built["type_"]),
        )

    def to_built(self) -> BuiltTrigger:
        return BuiltTrigger(
            Identifier=self.identifier,
            IsEnabled=self.is_enabled,
            DefinitionIdentifier=self.playbook_id,
            Type=self.type_.value,
            LogicalOperator=self.logical_operator.value,
            Conditions=[Condition.to_built(c) for c in self.conditions],
            Environments=self.environments,
            WorkflowName=self.playbook_name,
        )

    def to_non_built(self) -> NonBuiltTrigger:
        non_built: NonBuiltTrigger = NonBuiltTrigger(
            identifier=self.identifier,
            is_enabled=self.is_enabled,
            playbook_id=self.playbook_id,
            type_=self.type_.to_string(),
            conditions=[Condition.to_non_built(c) for c in self.conditions],
            logical_operator=self.logical_operator.to_string(),
            environments=self.environments,
            playbook_name=self.playbook_name,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
