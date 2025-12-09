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
import mp.core.utils
from mp.core.data_models.abc import ComponentMetadata, RepresentableEnum
from mp.core.data_models.condition.condition_group import (
    BuiltConditionGroup,
    ConditionGroup,
    NonBuiltConditionGroup,
)
from mp.core.data_models.widget.data import (
    BuiltWidgetDataDefinition,
    HtmlWidgetDataDefinition,
    NonBuiltWidgetDataDefinition,
    WidgetSize,
    WidgetType,
)

if TYPE_CHECKING:
    from pathlib import Path


class WidgetScope(RepresentableEnum):
    ALERT = 0
    CASE = 1


class BuiltActionWidgetMetadata(TypedDict):
    Title: str
    Type: int
    Scope: int
    ActionIdentifier: str | None
    Description: str
    DataDefinition: BuiltWidgetDataDefinition
    ConditionsGroup: BuiltConditionGroup
    DefaultSize: int


class NonBuiltActionWidgetMetadata(TypedDict):
    title: str
    type: str
    scope: str
    action_identifier: NotRequired[str | None]
    description: str
    data_definition: NonBuiltWidgetDataDefinition
    condition_group: NonBuiltConditionGroup
    default_size: str


class ActionWidgetMetadata(
    ComponentMetadata[BuiltActionWidgetMetadata, NonBuiltActionWidgetMetadata]
):
    file_name: str
    title: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    type_: WidgetType
    scope: WidgetScope
    action_identifier: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    data_definition: HtmlWidgetDataDefinition
    condition_group: ConditionGroup
    default_size: WidgetSize

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A sequence of `WidgetMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.OUT_WIDGETS_META_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.WIDGETS_META_SUFFIX}")
        ]

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the "non-built" integration

        Returns:
            A list of `WidgetMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.WIDGETS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_non_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltActionWidgetMetadata) -> Self:
        return cls(
            file_name=file_name,
            title=built["Title"],
            type_=WidgetType(built["Type"]),
            scope=WidgetScope(built.get("Scope", WidgetScope.ALERT.value)),
            action_identifier=built["ActionIdentifier"],
            description=built["Description"],
            data_definition=HtmlWidgetDataDefinition.from_built("", built["DataDefinition"]),
            condition_group=ConditionGroup.from_built(built["ConditionsGroup"]),
            default_size=WidgetSize(built["DefaultSize"]),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltActionWidgetMetadata) -> Self:
        return cls(
            file_name=file_name,
            title=non_built["title"],
            type_=WidgetType.from_string(non_built["type"]),
            scope=WidgetScope.from_string(
                non_built.get("scope", WidgetScope.ALERT.to_string()),
            ),
            action_identifier=non_built["action_identifier"],
            description=non_built["description"],
            data_definition=HtmlWidgetDataDefinition.from_non_built(
                "",
                non_built["data_definition"],
            ),
            condition_group=ConditionGroup.from_non_built(non_built["condition_group"]),
            default_size=WidgetSize.from_string(non_built["default_size"]),
        )

    def to_built(self) -> BuiltActionWidgetMetadata:
        """Create a built widget metadata dict.

        Returns:
            A built version of the widget metadata dict

        """
        return BuiltActionWidgetMetadata(
            Title=self.title,
            Type=self.type_.value,
            Scope=self.scope.value,
            ActionIdentifier=self.action_identifier,
            Description=self.description,
            DataDefinition=self.data_definition.to_built(),
            ConditionsGroup=self.condition_group.to_built(),
            DefaultSize=self.default_size.value,
        )

    def to_non_built(self) -> NonBuiltActionWidgetMetadata:
        """Create a non-built widget metadata dict.

        Returns:
            A non-built version of the widget metadata dict

        """
        non_built: NonBuiltActionWidgetMetadata = NonBuiltActionWidgetMetadata(
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
