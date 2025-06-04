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

from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils

from .condition_group import BuiltConditionGroup, ConditionGroup, NonBuiltConditionGroup
from .data_definition import (
    BuiltWidgetDataDefinition,
    NonBuiltWidgetDataDefinition,
    WidgetDataDefinition,
    WidgetType,
)

if TYPE_CHECKING:
    import pathlib


class WidgetScope(mp.core.data_models.abc.RepresentableEnum):
    ALERT = 0
    CASE = 1


class WidgetSize(mp.core.data_models.abc.RepresentableEnum):
    HALF_WIDTH = 1
    FULL_WIDTH = 2
    THIRD_WIDTH = 3
    TWO_THIRDS_WIDTH = 4


class BuiltWidgetMetadata(TypedDict):
    title: str
    type: int
    scope: int
    actionIdentifier: str | None
    description: str
    dataDefinition: BuiltWidgetDataDefinition
    conditionsGroup: BuiltConditionGroup
    defaultSize: int


class NonBuiltWidgetMetadata(TypedDict):
    title: str
    type: str
    scope: str
    action_identifier: NotRequired[str | None]
    description: str
    data_definition: NonBuiltWidgetDataDefinition
    condition_group: NonBuiltConditionGroup
    default_size: str


class WidgetMetadata(
    mp.core.data_models.abc.ScriptMetadata[BuiltWidgetMetadata, NonBuiltWidgetMetadata],
):
    file_name: str
    title: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.PARAM_DISPLAY_NAME_REGEX,
        ),
    ]
    type_: WidgetType
    scope: WidgetScope
    action_identifier: Annotated[
        str | None,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    description: Annotated[
        str, pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH)
    ]
    data_definition: WidgetDataDefinition
    condition_group: ConditionGroup
    default_size: WidgetSize

    @classmethod
    def from_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A sequence of `WidgetMetadata` objects

        """
        meta_path: pathlib.Path = path / mp.core.constants.OUT_WIDGETS_META_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_integration_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.WIDGETS_META_SUFFIX}")
        ]

    @classmethod
    def from_non_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the "non-built" integration

        Returns:
            A list of `WidgetMetadata` objects

        """
        meta_path: pathlib.Path = path / mp.core.constants.WIDGETS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_non_built_integration_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltWidgetMetadata) -> WidgetMetadata:
        return cls(
            file_name=file_name,
            title=built["title"],
            type_=WidgetType(built["type"]),
            scope=WidgetScope(built.get("scope", WidgetScope.ALERT.value)),
            action_identifier=built["actionIdentifier"],
            description=built["description"],
            data_definition=WidgetDataDefinition.from_built(built["dataDefinition"]),
            condition_group=ConditionGroup.from_built(built["conditionsGroup"]),
            default_size=WidgetSize(built["defaultSize"]),
        )

    @classmethod
    def _from_non_built(
        cls,
        file_name: str,
        non_built: NonBuiltWidgetMetadata,
    ) -> WidgetMetadata:
        return cls(
            file_name=file_name,
            title=non_built["title"],
            type_=WidgetType.from_string(non_built["type"]),
            scope=WidgetScope.from_string(
                non_built.get("scope", WidgetScope.ALERT.to_string()),
            ),
            action_identifier=non_built["action_identifier"],
            description=non_built["description"],
            data_definition=WidgetDataDefinition.from_non_built(
                non_built["data_definition"],
            ),
            condition_group=ConditionGroup.from_non_built(non_built["condition_group"]),
            default_size=WidgetSize.from_string(non_built["default_size"]),
        )

    def to_built(self) -> BuiltWidgetMetadata:
        """Create a built widget metadata dict.

        Returns:
            A built version of the widget metadata dict

        """
        return BuiltWidgetMetadata(
            title=self.title,
            type=self.type_.value,
            scope=self.scope.value,
            actionIdentifier=self.action_identifier,
            description=self.description,
            dataDefinition=self.data_definition.to_built(),
            conditionsGroup=self.condition_group.to_built(),
            defaultSize=self.default_size.value,
        )

    def to_non_built(self) -> NonBuiltWidgetMetadata:
        """Create a non-built widget metadata dict.

        Returns:
            A non-built version of the widget metadata dict

        """
        non_built: NonBuiltWidgetMetadata = NonBuiltWidgetMetadata(
            title=self.title,
            type=self.type_.to_string(),
            scope=self.scope.to_string(),
            action_identifier=self.action_identifier,
            description=self.description,
            data_definition=self.data_definition.to_non_built(),
            condition_group=self.condition_group.to_non_built(),
            default_size=self.default_size.to_string(),
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
