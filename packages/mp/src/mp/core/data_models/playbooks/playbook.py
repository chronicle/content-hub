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
from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic
import yaml

import mp.core.constants
from mp.core.data_models.common.release_notes.metadata import NonBuiltReleaseNote, ReleaseNote
from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo
from mp.core.data_models.playbooks.meta.metadata import (
    BuiltPlaybookMetadata,
    NonBuiltPlaybookMetadata,
    PlaybookMetadata,
)
from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.data_models.playbooks.trigger.metadata import Trigger
from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.meta.access_permissions import (
        BuiltAccessPermission,
    )
    from mp.core.data_models.playbooks.trigger.metadata import (
        BuiltTrigger,
        NonBuiltTrigger,
    )
    from mp.core.data_models.playbooks.widget.metadata import (
        BuiltPlaybookWidgetMetadata,
        NonBuiltPlaybookWidgetMetadata,
    )

    from .meta.display_info import NonBuiltPlaybookDisplayInfo
    from .overview.metadata import BuiltOverview, BuiltOverviewDetails, NonBuiltOverview
    from .step.metadata import BuiltStep, NonBuiltStep


EMPTY_RN: ReleaseNote = ReleaseNote(
    description="Release description",
    new=True,
    item_name="Playbook name",
    item_type="Playbook",
    publish_time=1762436207,
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
    IsEnable: bool
    Version: float
    IsArchived: bool
    IsAutomatic: bool
    Name: Annotated[str, pydantic.Field(max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH)]
    Category: int
    Description: str
    Priority: int
    Creator: str
    VersionCreator: str | None
    VersionComment: str | None
    OriginalWorkflowIdentifier: str
    TemplateName: str | None
    PlaybookType: int
    IsDebugMode: bool
    DebugBaseAlertIdentifier: str | None
    DebugAlertIdentifier: str | None
    SimulationClone: NotRequired[bool | None]
    DefaultAccessLevel: NotRequired[int | None]
    CreationSource: NotRequired[int | None]
    Steps: list[BuiltStep]
    Triggers: list[BuiltTrigger]
    OverviewTemplates: list[BuiltOverviewDetails]
    Permissions: list[BuiltAccessPermission]
    Environments: list[str]


class BuiltPlaybook(TypedDict):
    CategoryName: str
    OverviewTemplatesDetails: list[BuiltOverview]
    WidgetTemplates: list[BuiltPlaybookWidgetMetadata]
    Definition: BuiltPlaybookDefinition


class NonBuiltPlaybook(TypedDict):
    steps: list[NonBuiltStep]
    trigger: NonBuiltTrigger
    overviews: list[NonBuiltOverview]
    widgets: list[NonBuiltPlaybookWidgetMetadata]
    release_notes: list[NonBuiltReleaseNote]
    meta_data: NonBuiltPlaybookMetadata
    display_info: NonBuiltPlaybookDisplayInfo


@dataclasses.dataclass(slots=True)
class Playbook:
    steps: list[Step]
    overviews: list[Overview]
    widgets: list[PlaybookWidgetMetadata]
    trigger: Trigger
    release_notes: list[ReleaseNote]
    meta_data: PlaybookMetadata
    display_info: PlaybookDisplayInfo

    @classmethod
    def from_built_path(cls, path: Path) -> Self:
        """Create a Playbook from a built playbook path.

        Args:
            path: The path to the "built" playbook.

        Returns:
            A Playbook object.

        """
        return cls(
            steps=Step.from_built_path(path),
            overviews=Overview.from_built_path(path),
            widgets=PlaybookWidgetMetadata.from_built_path(path),
            trigger=Trigger.from_built_path(path),
            release_notes=[EMPTY_RN],
            meta_data=PlaybookMetadata.from_built_path(path),
            display_info=PlaybookDisplayInfo.from_built({}),  # ty:ignore[missing-typed-dict-key, invalid-argument-type]
        )

    @classmethod
    def from_non_built_path(cls, path: Path) -> Self:
        """Create a Playbook from a non-built playbook path.

        Args:
            path: The path to the "non-built" playbook directory.

        Returns:
            A Playbook object.

        """
        display_info_path: Path = path / mp.core.constants.DISPLAY_INFO_FILE_MAME
        return cls(
            steps=Step.from_non_built_path(path),
            overviews=Overview.from_non_built_path(path),
            widgets=PlaybookWidgetMetadata.from_non_built_path(path),
            trigger=Trigger.from_non_built_path(path),
            release_notes=ReleaseNote.from_non_built_path(path),
            meta_data=PlaybookMetadata.from_non_built_path(path),
            display_info=(
                PlaybookDisplayInfo.from_non_built(
                    yaml.safe_load(display_info_path.read_text(encoding="utf-8"))
                )
            ),
        )

    def to_built(self) -> BuiltPlaybook:
        """Convert the Playbook to its "built" representation.

        Returns:
            A BuiltPlaybook dictionary.

        """
        built_widgets: list[BuiltPlaybookWidgetMetadata] = [
            widget.to_built() for widget in self.widgets
        ]

        built_overviews: list[BuiltOverview] = [overview.to_built() for overview in self.overviews]
        built_overviews_for_definition: list[BuiltOverviewDetails] = [
            b_o["OverviewTemplate"] for b_o in built_overviews
        ]

        built_playbook_meta: BuiltPlaybookMetadata = self.meta_data.to_built()
        steps: list[BuiltStep] = [step.to_built() for step in self.steps]
        trigger: list[BuiltTrigger] = [self.trigger.to_built()]

        built_playbook_definition: BuiltPlaybookDefinition = BuiltPlaybookDefinition(
            Identifier=built_playbook_meta["Identifier"],
            IsEnable=built_playbook_meta["IsEnable"],
            Version=built_playbook_meta["Version"],
            IsArchived=built_playbook_meta["IsArchived"],
            IsAutomatic=built_playbook_meta["IsAutomatic"],
            Name=built_playbook_meta["Name"],
            Category=built_playbook_meta["Category"],
            Description=built_playbook_meta["Description"],
            Priority=built_playbook_meta["Priority"],
            Creator=built_playbook_meta["Creator"],
            VersionCreator=built_playbook_meta["VersionCreator"],
            VersionComment=built_playbook_meta["VersionComment"],
            OriginalWorkflowIdentifier=built_playbook_meta["OriginalWorkflowIdentifier"],
            TemplateName=built_playbook_meta["TemplateName"],
            PlaybookType=built_playbook_meta["PlaybookType"],
            IsDebugMode=built_playbook_meta["IsDebugMode"],
            DebugBaseAlertIdentifier=built_playbook_meta["DebugBaseAlertIdentifier"],
            DebugAlertIdentifier=built_playbook_meta["DebugAlertIdentifier"],
            SimulationClone=built_playbook_meta["SimulationClone"],
            DefaultAccessLevel=built_playbook_meta["DefaultAccessLevel"],
            CreationSource=built_playbook_meta["CreationSource"],
            Steps=steps,
            Triggers=trigger,
            OverviewTemplates=built_overviews_for_definition,
            Permissions=built_playbook_meta["Permissions"],
            Environments=built_playbook_meta["Environments"],
        )

        return BuiltPlaybook(
            CategoryName="Content Hub",
            OverviewTemplatesDetails=built_overviews,
            WidgetTemplates=built_widgets,
            Definition=built_playbook_definition,
        )

    def to_non_built(self) -> NonBuiltPlaybook:
        """Convert the Playbook to its "non-built" representation.

        Returns:
            A NonBuiltPlaybook dictionary.

        """
        return NonBuiltPlaybook(
            steps=[step.to_non_built() for step in self.steps],
            overviews=[overview.to_non_built() for overview in self.overviews],
            widgets=[widget.to_non_built() for widget in self.widgets],
            trigger=self.trigger.to_non_built(),
            release_notes=[rn.to_non_built() for rn in self.release_notes],
            meta_data=self.meta_data.to_non_built(),
            display_info=self.display_info.to_non_built(),
        )
