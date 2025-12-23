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
from typing import TYPE_CHECKING, Any, Self, TypedDict

import pydantic  # noqa: TC002

import mp.core.constants
import mp.core.utils
from mp.core.data_models.abc import ComponentMetadata
from mp.core.data_models.common.condition.condition_group import (
    BuiltConditionGroup,
    ConditionGroup,
    NonBuiltConditionGroup,
)
from mp.core.data_models.common.widget.data import (
    BuiltWidgetDataDefinition,
    HtmlWidgetDataDefinition,
    NonBuiltWidgetDataDefinition,
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
    IntegrationName: str | None


class NonBuiltPlaybookWidgetMetadata(TypedDict):
    title: str
    description: str
    identifier: str
    order: int
    template_identifier: str
    type: str
    data_definition: NonBuiltWidgetDataDefinition | pydantic.Json[Any]
    widget_size: str
    action_widget_template_id: str | None
    step_id: str | None
    step_integration: str | None
    block_step_id: str | None
    block_step_instance_name: str | None
    present_if_empty: bool
    conditions_group: NonBuiltConditionGroup
    integration_name: str | None


class PlaybookWidgetMetadata(
    ComponentMetadata[BuiltPlaybookWidgetMetadata, NonBuiltPlaybookWidgetMetadata]
):
    title: str
    description: str
    identifier: str
    order: int
    template_identifier: str
    type: WidgetType
    data_definition: HtmlWidgetDataDefinition | pydantic.Json[Any]
    widget_size: WidgetSize
    action_widget_template_id: str | None
    step_id: str | None
    step_integration: str | None
    block_step_id: str | None
    block_step_instance_name: str | None
    present_if_empty: bool
    conditions_group: ConditionGroup
    integration_name: str | None

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A sequence of `WidgetMetadata` objects

        Raises:
            ValueError: If the file at `path` fails to load or parse as JSON.

        """
        if not path.exists():
            return []

        built_playbook: str = path.read_text(encoding="utf-8")

        try:
            full_playbook = json.loads(built_playbook)
            built_widget: list[BuiltPlaybookWidgetMetadata] = full_playbook["WidgetTemplates"]
            return [cls._from_built("", widget) for widget in built_widget]

        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {path}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e

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
        data_json: pydantic.Json | BuiltWidgetDataDefinition = json.loads(
            built["DataDefinitionJson"]
        )
        return cls(
            title=built["Title"],
            description=built["Description"],
            identifier=built["Identifier"],
            order=built["Order"],
            template_identifier=built["TemplateIdentifier"],
            type=WidgetType(built["Type"]),
            data_definition=(
                HtmlWidgetDataDefinition.from_built(file_name, data_json)
                if built["Type"] == WidgetType.HTML.value
                else built["DataDefinitionJson"]
            ),
            widget_size=WidgetSize(built["GridColumns"]),
            action_widget_template_id=built["ActionWidgetTemplateIdentifier"],
            step_id=built["StepIdentifier"],
            step_integration=built["StepIntegration"],
            block_step_id=built["BlockStepIdentifier"],
            block_step_instance_name=built["BlockStepInstanceName"],
            present_if_empty=built["PresentIfEmpty"],
            conditions_group=ConditionGroup.from_built(built["ConditionsGroup"]),
            integration_name=built["IntegrationName"],
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltPlaybookWidgetMetadata) -> Self:
        return cls(
            title=non_built["title"],
            description=non_built["description"],
            identifier=non_built["identifier"],
            order=non_built["order"],
            template_identifier=non_built["template_identifier"],
            type=WidgetType.from_string(non_built["type"]),
            data_definition=(
                HtmlWidgetDataDefinition.from_non_built(file_name, non_built["data_definition"])
                if non_built["type"] == WidgetType.HTML.to_string()
                else json.dumps(non_built["data_definition"])
            ),
            widget_size=WidgetSize.from_string(non_built["widget_size"]),
            action_widget_template_id=non_built["action_widget_template_id"],
            step_id=non_built["step_id"],
            step_integration=non_built["step_integration"],
            block_step_id=non_built["block_step_id"],
            block_step_instance_name=non_built["block_step_instance_name"],
            present_if_empty=non_built["present_if_empty"],
            conditions_group=ConditionGroup.from_non_built(non_built["conditions_group"]),
            integration_name=non_built["integration_name"],
        )

    def to_built(self) -> BuiltPlaybookWidgetMetadata:
        """Create a built widget metadata dict.

        Returns:
            A built version of the widget metadata dict

        """
        return BuiltPlaybookWidgetMetadata(
            Title=self.title,
            Description=self.description,
            Identifier=self.identifier,
            Order=self.order,
            TemplateIdentifier=self.template_identifier,
            Type=self.type.value,
            DataDefinitionJson=json.dumps(
                self.data_definition.to_built()
                if self.type == WidgetType.HTML
                else self.data_definition
            ),
            GridColumns=self.widget_size.value,
            ActionWidgetTemplateIdentifier=self.action_widget_template_id,
            StepIdentifier=self.step_id,
            StepIntegration=self.step_integration,
            BlockStepIdentifier=self.block_step_id,
            BlockStepInstanceName=self.block_step_instance_name,
            PresentIfEmpty=self.present_if_empty,
            ConditionsGroup=self.conditions_group.to_built(),
            IntegrationName=self.integration_name,
        )

    def to_non_built(self) -> NonBuiltPlaybookWidgetMetadata:
        """Create a non-built widget metadata dict.

        Returns:
            A non-built version of the widget metadata dict

        """
        non_built: NonBuiltPlaybookWidgetMetadata = NonBuiltPlaybookWidgetMetadata(
            title=self.title,
            description=self.description,
            identifier=self.identifier,
            order=self.order,
            template_identifier=self.template_identifier,
            type=self.type.to_string(),
            block_step_instance_name=self.block_step_instance_name,
            data_definition=(
                self.data_definition.to_non_built()
                if self.type == WidgetType.HTML
                else self.data_definition
            ),
            widget_size=self.widget_size.to_string(),
            step_integration=self.step_integration,
            action_widget_template_id=self.action_widget_template_id,
            step_id=self.step_id,
            block_step_id=self.block_step_id,
            present_if_empty=self.present_if_empty,
            conditions_group=self.conditions_group.to_non_built(),
            integration_name=self.integration_name,
        )
        return non_built
