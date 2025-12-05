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
from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils

from .access_permissions import (
    AccessPermission,
    BuiltAccessPermission,
    NonBuiltAccessPermission,
    PlaybookAccessLevel,
)
from .display_info import PlaybookType

if TYPE_CHECKING:
    from pathlib import Path


class PlaybookCreationSource(mp.core.data_models.abc.RepresentableEnum):
    """Represents the source of a playbook's creation."""

    USER_OR_API_INITIATED = 0
    AI_GENERATED_FROM_ALERT = 1
    AI_GENERATED_FROM_PROMPT = 2


class BuiltPlaybookMetadata(TypedDict):
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
    Permissions: list[BuiltAccessPermission]
    Environments: list[str]


class NonBuiltPlaybookMetadata(TypedDict):
    identifier: str
    is_enable: bool
    version: float
    name: str
    description: str
    creation_source: NotRequired[str | None]
    default_access_level: NotRequired[str | None]
    simulation_clone: NotRequired[bool | None]
    debug_alert_identifier: str | None
    debug_base_alert_identifier: str | None
    is_debug_mode: bool
    type: str
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
    permissions: list[NonBuiltAccessPermission]
    environments: list[str]


class PlaybookMetadata(
    mp.core.data_models.abc.ComponentMetadata[BuiltPlaybookMetadata, NonBuiltPlaybookMetadata]
):
    """Represents the metadata of a playbook."""

    identifier: str
    is_enable: bool
    version: float
    name: Annotated[
        str,
        pydantic.Field(
            pattern=mp.core.constants.NAME_VALIDATION_REGEX,
        ),
    ]
    description: str
    debug_alert_identifier: str | None
    debug_base_alert_identifier: str | None
    is_debug_mode: bool
    type_: PlaybookType
    template_name: str | None
    original_workflow_identifier: str
    version_comment: str | None
    version_creator: str | None
    creator: str
    priority: int
    category: int
    is_automatic: bool
    is_archived: bool
    permissions: list[AccessPermission]
    last_editor: str | None = None
    creation_source: PlaybookCreationSource | None = None
    default_access_level: PlaybookAccessLevel | None = None
    simulation_clone: bool | None = None
    environments: list[str] = []  # noqa: RUF012

    @classmethod
    def from_built_path(cls, path: Path) -> Self:
        """Create a PlaybookMetadata object from a built playbook path.

        Args:
            path: The path to the built playbook.

        Returns:
            A PlaybookMetadata object.

        Raises:
            ValueError: If the file at `path` fails to load or parse as JSON.

        """
        if not path.exists():
            return []

        built_playbook: str = path.read_text(encoding="utf-8")

        try:
            full_playbook = json.loads(built_playbook)
            return cls._from_built("", full_playbook["Definition"])

        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {path}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e

    @classmethod
    def from_non_built_path(cls, path: Path) -> Self:
        """Create a PlaybookMetadata object from a non-built playbook path.

        Args:
            path: The path to the non-built playbook directory.

        Returns:
            A PlaybookMetadata object.

        """
        definition_path: Path = path / mp.core.constants.DEFINITION_FILE
        if definition_path.exists():
            return cls._from_non_built_path(definition_path)
        return None

    @classmethod
    def _from_built(cls, _: str, built: BuiltPlaybookMetadata) -> Self:
        access_level: int | None = built.get("DefaultAccessLevel")
        creation_source: int | None = built.get("CreationSource")
        return cls(
            identifier=built["Identifier"],
            is_enable=built["IsEnable"],
            version=built["Version"],
            name=built["Name"],
            description=built["Description"],
            debug_alert_identifier=built["DebugAlertIdentifier"],
            debug_base_alert_identifier=built["DebugBaseAlertIdentifier"],
            is_debug_mode=built["IsDebugMode"],
            type_=PlaybookType(int(built["PlaybookType"])),
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
            default_access_level=(
                PlaybookAccessLevel(int(access_level)) if access_level is not None else None
            ),
            creation_source=(
                PlaybookCreationSource(int(creation_source))
                if creation_source is not None
                else None
            ),
            simulation_clone=built.get("SimulationClone"),
            permissions=[AccessPermission.from_built(p) for p in built["Permissions"]],
            environments=built.get("Environments", []),
        )

    @classmethod
    def _from_non_built(cls, _: str, non_built: NonBuiltPlaybookMetadata) -> Self:
        access_level: str | None = non_built.get("default_access_level")
        creation_source: str | None = non_built.get("creation_source")
        return cls(
            identifier=non_built["identifier"],
            is_enable=non_built["is_enable"],
            version=non_built["version"],
            name=non_built["name"],
            description=non_built["description"],
            debug_alert_identifier=non_built["debug_alert_identifier"],
            debug_base_alert_identifier=non_built["debug_base_alert_identifier"],
            is_debug_mode=non_built["is_debug_mode"],
            type_=PlaybookType.from_string(non_built["type"]),
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
            default_access_level=(
                PlaybookAccessLevel.from_string(access_level) if access_level is not None else None
            ),
            creation_source=(
                PlaybookCreationSource.from_string(creation_source)
                if creation_source is not None
                else None
            ),
            simulation_clone=non_built.get("simulation_clone"),
            permissions=[AccessPermission.from_non_built(p) for p in non_built["permissions"]],
            environments=non_built.get("environments", []),
        )

    def to_built(self) -> BuiltPlaybookMetadata:
        """Convert the PlaybookMetadata to its "built" representation.

        Returns:
            A BuiltPlaybookMetadata dictionary.

        """
        return BuiltPlaybookMetadata(
            Identifier=self.identifier,
            IsEnable=self.is_enable,
            Version=self.version,
            Name=self.name,
            Description=self.description,
            DebugAlertIdentifier=self.debug_alert_identifier,
            DebugBaseAlertIdentifier=self.debug_base_alert_identifier,
            IsDebugMode=self.is_debug_mode,
            PlaybookType=self.type_.value,
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
            DefaultAccessLevel=(
                self.default_access_level.value if self.default_access_level is not None else None
            ),
            CreationSource=self.creation_source.value if self.creation_source is not None else None,
            SimulationClone=self.simulation_clone,
            Permissions=[p.to_built() for p in self.permissions],
            Environments=self.environments,
        )

    def to_non_built(self) -> NonBuiltPlaybookMetadata:
        """Convert the PlaybookMetadata to its "non-built" representation.

        Returns:
            A NonBuiltPlaybookMetadata dictionary.

        """
        non_built: NonBuiltPlaybookMetadata = NonBuiltPlaybookMetadata(
            identifier=self.identifier,
            is_enable=self.is_enable,
            version=self.version,
            name=self.name,
            description=self.description,
            debug_alert_identifier=self.debug_alert_identifier,
            debug_base_alert_identifier=self.debug_base_alert_identifier,
            is_debug_mode=self.is_debug_mode,
            type=self.type_.to_string(),
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
            default_access_level=self.default_access_level.to_string()
            if self.default_access_level is not None
            else None,
            creation_source=self.creation_source.to_string()
            if self.creation_source is not None
            else None,
            simulation_clone=self.simulation_clone,
            permissions=[p.to_non_built() for p in self.permissions],
            environments=self.environments,
        )
        return non_built
