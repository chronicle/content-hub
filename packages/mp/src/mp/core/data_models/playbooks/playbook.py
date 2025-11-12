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
import json
import yaml
from typing import TYPE_CHECKING, Annotated, NotRequired, TypedDict, Self

import pydantic
from pathlib import Path

import mp.core.constants
from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.core.data_models.playbooks.playbook_widget.metadata import PlaybookWidgetMetadata
from mp.core.data_models.playbooks.trigger.metadata import Trigger
from mp.core.data_models.playbooks.playbook_meta.metadata import (
    PlaybookMetadata,
    NonBuiltPlaybookMetadata,
    BuiltPlaybookMetadata,
)
from mp.core.data_models.playbooks.playbook_meta.display_info import PlaybookDisplayInfo
from mp.core.data_models.release_notes.metadata import ReleaseNote, NonBuiltReleaseNote

if TYPE_CHECKING:
    from .overview.metadata import BuiltOverview, NonBuiltOverview
    from packages.mp.src.mp.core.data_models.playbooks.playbook_meta.access_permissions import (
        BuiltAccessPermission,
    )
    from packages.mp.src.mp.core.data_models.playbooks.playbook_widget import (
        BuiltPlaybookWidgetMetadata,
        NonBuiltPlaybookWidgetMetadata,
    )
    from .step.metadata import BuiltStep, NonBuiltStep
    from .playbook_meta.display_info import NonBuiltPlaybookDisplayInfo
    from packages.mp.src.mp.core.data_models.playbooks.trigger.metadata import ( BuiltTrigger, NonBuiltTrigger)


EMPTY_RN: ReleaseNote = ReleaseNote(
    description="Release description",
    new=True,
    item_name="Playbook name",
    item_type="Playbook",
    publish_time="1762436207",
    regressive=False,
    removed=False,
    ticket=None,
    version=1.0,
)

class BuiltPlaybookOverviewTemplateDetails(TypedDict):
    OverviewTemplate: BuiltOverview
    Roles: list[str]


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


class BuiltPlaybook(TypedDict):
    CategoryName: str
    OverviewTemplatesDetails: list[BuiltPlaybookOverviewTemplateDetails]
    WidgetTemplates: list[BuiltPlaybookWidgetMetadata]
    Definition: BuiltPlaybookDefinition


class NonBuiltPlaybook(TypedDict):
    steps: list[NonBuiltStep]
    triggers: list[NonBuiltTrigger]
    overviews: list[NonBuiltOverview]
    widgets: list[NonBuiltPlaybookWidgetMetadata]
    release_notes: list[NonBuiltReleaseNote]
    meta_data: NonBuiltPlaybookMetadata
    display_info: NonBuiltPlaybookDisplayInfo

@dataclasses.dataclass(slots=True, frozen=True)
class Playbook:
    steps: list[Step]
    overviews: list[Overview]
    widgets: list[PlaybookWidgetMetadata]
    triggers: list[Trigger]
    release_notes: list[ReleaseNote]
    meta_data: PlaybookMetadata
    display_info: PlaybookDisplayInfo

    @classmethod
    def from_built_path(cls, path: Path) -> Self:
        """Create the Playbook from a built playbook path.

        Args:
             path: the path to the "built" playbook.

        Returns:
            The Playbook object.

        """
        return cls(
            steps=Step.from_built_path(path),
            overviews=Overview.from_built_path(path),
            widgets=PlaybookWidgetMetadata.from_built_path(path),
            triggers=Trigger.from_built_path(path),
            release_notes=[EMPTY_RN],
            meta_data=PlaybookMetadata.from_built_path(path),
            display_info=PlaybookDisplayInfo.from_built({}),
        )

    @classmethod
    def from_non_built_path(cls, path: Path):
        display_info_path: Path = path / mp.core.constants.DISPLAY_INFO_FILE_MAME
        return cls(
            steps=Step.from_non_built_path(path),
            overviews=Overview.from_non_built_path(path),
            widgets=PlaybookWidgetMetadata.from_non_built_path(path),
            triggers=Trigger.from_non_built_path(path),
            release_notes=ReleaseNote.from_non_built_path(path),
            meta_data=PlaybookMetadata.from_non_built_path(path),
            display_info=(
                PlaybookDisplayInfo.from_non_built(yaml.safe_load(display_info_path.read_text(encoding="utf-8")))
            ),
        )

    def to_built(self) -> BuiltPlaybook:
        built_widgets: list[BuiltPlaybookWidgetMetadata] = [widget.to_built() for widget in self.widgets]
        built_overviews: list[BuiltOverview] = [overview.to_built_with_widget(built_widgets) for overview in self.overviews]
    
        built_playbook_meta: BuiltPlaybookMetadata = self.meta_data.to_built()
        steps: list[BuiltStep] = [step.to_built() for step in self.steps]
        triggers: list[BuiltTrigger] = [trigger.to_built() for trigger in self.triggers]

        built_playbook_definition: BuiltPlaybookDefinition = BuiltPlaybookDefinition(
            Identifier=built_playbook_meta["Identifier"],
            Name=built_playbook_meta["Name"],
            IsEnable=built_playbook_meta["IsEnable"],
            Version=built_playbook_meta["Version"],
            Description=built_playbook_meta["Description"],
            CreationSource=built_playbook_meta["CreationSource"],
            DefaultAccessLevel=built_playbook_meta["DefaultAccessLevel"],
            SimulationClone=built_playbook_meta["SimulationClone"],
            DebugAlertIdentifier=built_playbook_meta["DebugAlertIdentifier"],
            DebugBaseAlertIdentifier=built_playbook_meta["DebugBaseAlertIdentifier"],
            IsDebugMode=built_playbook_meta["IsDebugMode"],
            PlaybookType=built_playbook_meta["PlaybookType"],
            TemplateName=built_playbook_meta["TemplateName"],
            OriginalWorkflowIdentifier=built_playbook_meta["OriginalWorkflowIdentifier"],
            VersionComment=built_playbook_meta["VersionComment"],
            VersionCreator=built_playbook_meta["VersionCreator"],
            LastEditor=built_playbook_meta["LastEditor"],
            Creator=built_playbook_meta["Creator"],
            Priority=built_playbook_meta["Priority"],
            Category=built_playbook_meta["Category"],
            IsAutomatic=built_playbook_meta["IsAutomatic"],
            IsArchived=built_playbook_meta["IsArchived"],
            Steps=steps,
            Triggers=triggers,
            OverviewTemplates=built_overviews,
            Permissions=built_playbook_meta["Permissions"],
        )

        built_playbook_overview_template_details: list[BuiltPlaybookOverviewTemplateDetails] = [
            overview.to_built_with_widget(built_widgets)
            for overview in self.overviews
        ]

        return BuiltPlaybook(
            CategoryName="Content Hub",
            OverviewTemplatesDetails=built_playbook_overview_template_details,
            WidgetTemplates=built_widgets,
            Definition=built_playbook_definition,
        )

    def to_non_built(self) -> NonBuiltPlaybook:
        return NonBuiltPlaybook(
            steps=[step.to_non_built() for step in self.steps],
            overviews=[overview.to_non_built() for overview in self.overviews],
            widgets=[widget.to_non_built() for widget in self.widgets],
            triggers=[trigger.to_non_built() for trigger in self.triggers],
            release_notes=[rn.to_non_built() for rn in self.release_notes],
            meta_data=self.meta_data.to_non_built(),
            display_info=self.display_info.to_non_built(),
        )
