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

from typing import Annotated, Self, TypedDict, NotRequired

import pydantic

import mp.core.constants
import mp.core.utils
import mp.core.data_models.abc


class PlaybookCreationSource(mp.core.data_models.abc.RepresentableEnum):
    USER_OR_API_INITIATED = 0
    AI_GENERATED_FROM_ALERT = 1
    AI_GENERATED_FROM_PROMPT = 2


class PlaybookAccessLevel(mp.core.data_models.abc.RepresentableEnum):
    NO_ACCESS = 0
    VIEW = 1
    EDIT = 2


class PlaybookType(mp.core.data_models.abc.RepresentableEnum):
    PLAYBOOK = 0
    BLOCK = 1


class BuiltPlaybookMetadata(TypedDict):
    Identifier: Annotated[str, pydantic.Field(pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX)]
    Name: Annotated[str, pydantic.Field(max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH)]
    IsEnable: bool
    Version: float
    Description: str
    CreationSource: NotRequired[int| None]
    DefaultAccessLevel: NotRequired[int| None]
    SimulationClone: NotRequired[bool| None]
    DebugAlertIdentifier: str | None
    DebugBaseAlertIdentifier: str | None
    IsDebugMode: bool
    PlaybookType: int
    TemplateName: str | None
    OriginalWorkflowIdentifier: str
    VersionComment: str | None
    VersionCreator: str | None
    LastEditor: NotRequired[str| None]
    Creator: str
    Priority: int
    Category: int
    IsAutomatic: bool
    IsArchived: bool


class NonBuiltPlaybookMetadata(TypedDict):
    identifier: str
    is_enable: bool
    version: float
    name: str
    description: str
    creation_source: NotRequired[int | None]
    default_access_level: NotRequired[int | None]
    simulation_clone: NotRequired[bool | None]
    debug_alert_identifier: str | None
    debug_base_alert_identifier: str | None
    is_debug_mode: bool
    playbook_type: int
    template_name: str | None
    original_workflow_identifier: str
    version_comment: str | None
    version_creator: str | None
    last_editor: NotRequired[str | None]
    creator: str
    priority: int
    category: int
    is_automatic: bool
    is_archived: bool


class PlaybookMetadata(
    mp.core.data_models.abc.Buildable[BuiltPlaybookMetadata, NonBuiltPlaybookMetadata]
):
    identifier: str
    is_enable: bool
    version: float
    name: str
    description: str
    debug_alert_identifier: str | None
    debug_base_alert_identifier: str | None
    is_debug_mode: bool
    playbook_type: int
    template_name: str | None
    original_workflow_identifier: str
    version_comment: str | None
    version_creator: str | None
    creator: str
    priority: int
    category: int
    is_automatic: bool
    is_archived: bool
    last_editor: str | None = None
    creation_source: int | None = None
    default_access_level: int | None = None
    simulation_clone: bool | None = None

    @classmethod
    def _from_built(cls, built: BuiltPlaybookMetadata) -> Self:
        return cls(
            identifier=built["Identifier"],
            is_enable=built["IsEnable"],
            version=built["Version"],
            name=built["Name"],
            description=built["Description"],
            debug_alert_identifier=built["DebugAlertIdentifier"],
            debug_base_alert_identifier=built["DebugBaseAlertIdentifier"],
            is_debug_mode=built["IsDebugMode"],
            playbook_type=built["PlaybookType"],
            template_name=built["TemplateName"],
            original_workflow_identifier=built["OriginalWorkflowIdentifier"],
            version_comment=built["VersionComment"],
            version_creator=built["VersionCreator"],
            creator=built["Creator"],
            priority=built["Priority"],
            category=built["Category"],
            is_automatic=built["IsAutomatic"],
            is_archived=built["IsArchived"],
            last_editor=built.get("LastEditor"),
            default_access_level=built.get("DefaultAccessLevel"),
            creation_source=built.get("CreationSource"),
            simulation_clone=built.get("SimulationClone"),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltPlaybookMetadata) -> Self:
        return cls(
            identifier=non_built["identifier"],
            is_enable=non_built["is_enable"],
            version=non_built["version"],
            name=non_built["name"],
            description=non_built["description"],
            debug_alert_identifier=non_built["debug_alert_identifier"],
            debug_base_alert_identifier=non_built["debug_base_alert_identifier"],
            is_debug_mode=non_built["is_debug_mode"],
            playbook_type=non_built["playbook_type"],
            template_name=non_built["template_name"],
            original_workflow_identifier=non_built["original_workflow_identifier"],
            version_comment=non_built["version_comment"],
            version_creator=non_built["version_creator"],
            creator=non_built["creator"],
            priority=non_built["priority"],
            category=non_built["category"],
            is_automatic=non_built["is_automatic"],
            is_archived=non_built["is_archived"],
            last_editor=non_built.get("last_editor"),
            default_access_level=non_built.get("default_access_level"),
            creation_source=non_built.get("creation_source"),
            simulation_clone=non_built.get("simulation_clone"),
        )

    def to_built(self) -> BuiltPlaybookMetadata:
        return BuiltPlaybookMetadata(
            Identifier=self.identifier,
            IsEnable=self.is_enable,
            Version=self.version,
            Name=self.name,
            Description=self.description,
            DebugAlertIdentifier=self.debug_alert_identifier,
            DebugBaseAlertIdentifier=self.debug_base_alert_identifier,
            IsDebugMode=self.is_debug_mode,
            PlaybookType=self.playbook_type,
            TemplateName=self.template_name,
            OriginalWorkflowIdentifier=self.original_workflow_identifier,
            VersionComment=self.version_comment,
            VersionCreator=self.version_creator,
            Creator=self.creator,
            Priority=self.priority,
            Category=self.category,
            IsAutomatic=self.is_automatic,
            IsArchived=self.is_archived,
            LastEditor=self.last_editor,
            DefaultAccessLevel=self.default_access_level,
            CreationSource=self.creation_source,
            SimulationClone=self.simulation_clone,
        )

    def to_non_built(self) -> NonBuiltPlaybookMetadata:
        non_built: NonBuiltPlaybookMetadata = NonBuiltPlaybookMetadata(
            identifier=self.identifier,
            is_enable=self.is_enable,
            version=self.version,
            name=self.name,
            description=self.description,
            debug_alert_identifier=self.debug_alert_identifier,
            debug_base_alert_identifier=self.debug_base_alert_identifier,
            is_debug_mode=self.is_debug_mode,
            playbook_type=self.playbook_type,
            template_name=self.template_name,
            original_workflow_identifier=self.original_workflow_identifier,
            version_comment=self.version_comment,
            version_creator=self.version_creator,
            creator=self.creator,
            priority=self.priority,
            category=self.category,
            is_automatic=self.is_automatic,
            is_archived=self.is_archived,
            last_editor=self.last_editor,
            default_access_level=self.default_access_level,
            creation_source=self.creation_source,
            simulation_clone=self.simulation_clone,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
