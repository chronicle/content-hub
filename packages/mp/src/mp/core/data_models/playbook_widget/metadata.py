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

from typing import TYPE_CHECKING, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
from mp.core.data_models.condition import (
    BuiltConditionGroup,
    ConditionGroup,
    NonBuiltConditionGroup,
)
from mp.core.data_models.widget.data import (
    NonBuiltWidgetDataDefinition,
    HtmlWidgetDataDefinition,
    WidgetSize,
    WidgetType,
)

if TYPE_CHECKING:
    from pathlib import Path


class BuiltPlaybookWidgetMetadata(TypedDict):
    Title: str
    Description: str
    Identifier: str
    Order: int
    TemplateIdentifier: str
    Type: int
    DataDefinitionJson: str
    GridColumns: int
    ActionWidgetTemplateIdentifier: str | None
    StepIdentifier: str | None
    StepIntegration: str | None
    BlockStepIdentifier: str | None
    BlockStepInstanceName: str | None
    PresentIfEmpty: bool
    ConditionsGroup: BuiltConditionGroup
    IntegrationName: str


class NonBuiltPlaybookWidgetMetadata(TypedDict):
    title: str
    description: str
    identifier: str
    order: int
    template_identifier: str
    type: str
    data_definition: NonBuiltWidgetDataDefinition
    widget_size: str
    action_widget_template_id: str | None
    step_id: str | None
    step_integration: str | None
    block_step_id: str | None
    block_step_instance_name: str | None
    present_if_empty: bool
    present_if_empty: bool
    conditions_group: NonBuiltConditionGroup
    integration_name: str


class PlaybookWidgetMetadata(
    mp.core.data_models.abc.ComponentMetadata[
        BuiltPlaybookWidgetMetadata, NonBuiltPlaybookWidgetMetadata
    ]
):
    title: str
    description: str
    identifier: str
    order: int
    template_identifier: str
    type: WidgetType
    data_definition: HtmlWidgetDataDefinition | pydantic.Json
    widget_size: WidgetSize
    action_widget_template_id: str | None
    step_id: str | None
    step_integration: str | None
    block_step_id: str | None
    block_step_instance_name: str | None
    present_if_empty: bool
    conditions_group: ConditionGroup
    integration_name: str

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A sequence of `WidgetMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.WIDGETS_DIR
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
    def _from_built(cls, file_name: str, built: BuiltPlaybookWidgetMetadata) -> Self:
        return cls()

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltPlaybookWidgetMetadata) -> Self:
        return cls()

    def to_built(self) -> BuiltPlaybookWidgetMetadata:
        """Create a built widget metadata dict.

        Returns:
            A built version of the widget metadata dict

        """
        return BuiltPlaybookWidgetMetadata()

    def to_non_built(self) -> NonBuiltPlaybookWidgetMetadata:
        """Create a non-built widget metadata dict.

        Returns:
            A non-built version of the widget metadata dict

        """
        non_built: NonBuiltPlaybookWidgetMetadata = NonBuiltPlaybookWidgetMetadata()
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
