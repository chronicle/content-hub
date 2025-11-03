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

import dataclasses
from typing import TYPE_CHECKING, Annotated, NotRequired, TypedDict

import pydantic

import mp.core.constants

from packages.mp.src.mp.core.data_models.playbook.meta.display_info import NonBuiltPlaybookDisplayInfo, PlaybookDisplayInfo

if TYPE_CHECKING:
    from .overview.metadata import BuiltOverview, NonBuiltOverview
    from packages.mp.src.mp.core.data_models.playbook.meta.access_permissions import BuiltAccessPermission
    from packages.mp.src.mp.core.data_models.playbook.widget.metadata import (
        BuiltPlaybookWidgetMetadata,
        NonBuiltPlaybookWidgetMetadata,
        PlaybookWidgetMetadata,
    )
    from .step.metadata import BuiltStep, NonBuiltStep
    from packages.mp.src.mp.core.data_models.trigger.metadata import BuiltTrigger, NonBuiltTrigger


class BuiltPlaybook(TypedDict):
    CategoryName: str
    OverviewTemplatesDetails: BuiltPlaybookOverviewTemplateDetails
    WidgetTemplates: list[BuiltPlaybookWidgetMetadata]
    Definition: BuiltPlaybookDefinition


class BuiltPlaybookDefinition(TypedDict):
    Identifier: Annotated[str, pydantic.Field(pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX)]
    Name: Annotated[str, pydantic.Field(max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH)]
    IsEnable: bool
    Version: float
    Description: str
    CreationSource: NotRequired[int | None]
    DefaultAccessLevel: NotRequired[int | None]
    SimulationClone: NotRequired[bool | None]
    DebugAlertIdentifier: str | None
    DebugBaseAlertIdentifier: str | None
    IsDebugMode: bool
    PlaybookType: int
    TemplateName: str | None
    OriginalWorkflowIdentifier: str
    VersionComment: str | None
    VersionCreator: str | None
    LastEditor: NotRequired[str | None]
    Creator: str
    Priority: int
    Category: int
    IsAutomatic: bool
    IsArchived: bool
    Steps: list[BuiltStep]
    Triggers: list[BuiltTrigger]
    OverviewTemplates: list[BuiltOverview]
    Permissions: list[BuiltAccessPermission]


class BuiltPlaybookOverviewTemplateDetails(TypedDict):
    OverviewTemplate: list[BuiltOverview]
    Roles: list[str]


class NonBuiltPlaybook(TypedDict):
    metadata: NonBuiltPlaybook
    steps: list[NonBuiltStep]
    triggers: list[NonBuiltTrigger]
    overviews: list[NonBuiltOverview]
    widgets: list[NonBuiltPlaybookWidgetMetadata]
    display_info: NonBuiltPlaybookDisplayInfo


@dataclasses.dataclass(slots=True, frozen=True)
class Playbook:
    category_name: str
    overview_templates_details: BuiltPlaybookOverviewTemplateDetails
    widget_templates: list[PlaybookWidgetMetadata]
    definition: BuiltPlaybookDefinition

    
