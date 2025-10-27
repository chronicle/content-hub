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

import enum
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import mp.core.data_models.abc
from mp.core.data_models.condition import Condition, LogicalOperator  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.condition import BuiltCondition, NonBuiltCondition


class TriggerType(enum.Enum):
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
    WorkflowName: str | None
    LogicalOperator: int
    Conditions: list[BuiltCondition]
    Environments: list[str]


class NonBuiltTrigger(TypedDict):
    identifier: str
    is_enabled: bool
    playbook_id: str
    type_: TriggerType
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
        pass

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        pass

    @classmethod
    def _from_built(cls, built: BuiltTrigger) -> Self:
        pass

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltTrigger) -> Self:
        pass

    def to_built(self) -> BuiltTrigger:
        pass

    def to_non_built(self) -> NonBuiltTrigger:
        pass
