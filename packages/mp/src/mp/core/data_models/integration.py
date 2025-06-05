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
import decimal
import itertools
import tomllib
from typing import TYPE_CHECKING, Any, TypedDict

import mp.core.constants
import mp.core.file_utils
import mp.core.utils

from .action.metadata import ActionMetadata
from .connector.metadata import ConnectorMetadata
from .custom_families.metadata import CustomFamily
from .integration_meta.metadata import IntegrationMetadata, PythonVersion
from .job.metadata import JobMetadata
from .mapping_rules.metadata import MappingRule
from .release_notes.metadata import ReleaseNote
from .widget.metadata import WidgetMetadata

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Mapping, MutableMapping, Sequence

    from mp.core.custom_types import (
        ActionName,
        ConnectorName,
        JobName,
        ManagerName,
        WidgetName,
    )

    from .action.metadata import BuiltActionMetadata, NonBuiltActionMetadata
    from .connector.metadata import BuiltConnectorMetadata, NonBuiltConnectorMetadata
    from .custom_families.metadata import BuiltCustomFamily, NonBuiltCustomFamily
    from .integration_meta.metadata import (
        BuiltIntegrationMetadata,
        NonBuiltIntegrationMetadata,
    )
    from .integration_meta.parameter import BuiltIntegrationParameter
    from .job.metadata import BuiltJobMetadata, NonBuiltJobMetadata
    from .mapping_rules.metadata import BuiltMappingRule, NonBuiltMappingRule
    from .release_notes.metadata import BuiltReleaseNote, NonBuiltReleaseNote
    from .widget.metadata import BuiltWidgetMetadata, NonBuiltWidgetMetadata


class BuiltIntegration(TypedDict):
    metadata: BuiltIntegrationMetadata
    release_notes: Sequence[BuiltReleaseNote]
    mapping_rules: Sequence[BuiltMappingRule]
    custom_families: Sequence[BuiltCustomFamily]
    common_modules: Sequence[ManagerName]
    actions: Mapping[ActionName, BuiltActionMetadata]
    connectors: Mapping[ConnectorName, BuiltConnectorMetadata]
    jobs: Mapping[JobName, BuiltJobMetadata]
    widgets: Mapping[WidgetName, BuiltWidgetMetadata]


class NonBuiltIntegration(TypedDict):
    metadata: NonBuiltIntegrationMetadata
    release_notes: Sequence[NonBuiltReleaseNote]
    mapping_rules: Sequence[NonBuiltMappingRule]
    custom_families: Sequence[NonBuiltCustomFamily]
    common_modules: Sequence[ManagerName]
    actions: Mapping[ActionName, NonBuiltActionMetadata]
    connectors: Mapping[ConnectorName, NonBuiltConnectorMetadata]
    jobs: Mapping[JobName, NonBuiltJobMetadata]
    widgets: Mapping[WidgetName, NonBuiltWidgetMetadata]


class IntegrationPyProjectToml(TypedDict):
    project: MutableMapping[str, Any]


class FullDetailsReleaseNoteJson(TypedDict):
    Items: Sequence[str]
    Version: float
    PublishTimeUnixTime: int


class BuiltFullDetails(TypedDict):
    Identifier: str
    PackageName: str
    DisplayName: str
    Description: str
    DocumentationLink: str | None
    MinimumSystemVersion: float
    IntegrationProperties: Sequence[BuiltIntegrationParameter]
    Actions: Sequence[str]
    Jobs: Sequence[str]
    Connectors: Sequence[str]
    Managers: Sequence[str]
    CustomFamilies: Sequence[str]
    MappingRules: Sequence[str]
    Widgets: Sequence[str]
    Version: float
    IsCustom: bool
    ExampleUseCases: Sequence[str]
    ReleaseNotes: Sequence[FullDetailsReleaseNoteJson]


@dataclasses.dataclass(slots=True, frozen=True)
class Integration:
    identifier: str
    metadata: IntegrationMetadata
    release_notes: Sequence[ReleaseNote]
    custom_families: Sequence[CustomFamily]
    mapping_rules: Sequence[MappingRule]
    common_modules: Sequence[ManagerName]
    actions_metadata: Mapping[ActionName, ActionMetadata]
    connectors_metadata: Mapping[ConnectorName, ConnectorMetadata]
    jobs_metadata: Mapping[JobName, JobMetadata]
    widgets_metadata: Mapping[WidgetName, WidgetMetadata]

    def __post_init__(self) -> None:
        """Perform post-init logic."""
        self._validate_integration()

    def _validate_integration(self) -> None:
        """Perform various validations over the integration."""
        self._raise_error_if_custom()
        self._raise_error_if_disabled()
        self._raise_error_if_no_ping_action()

    @classmethod
    def from_built_path(cls, path: pathlib.Path) -> Integration:
        """Create the integration from a built integration's path.

        Args:
            path: the path to the "built" integration

        Returns:
            The integration objet

        Raises:
            ValueError: when the built integration failed to load

        """
        try:
            integration_meta: IntegrationMetadata = (
                IntegrationMetadata.from_built_integration_path(path)
            )
            return cls(
                identifier=integration_meta.identifier,
                metadata=integration_meta,
                release_notes=ReleaseNote.from_built_integration_path(path),
                custom_families=CustomFamily.from_built_integration_path(path),
                mapping_rules=MappingRule.from_built_integration_path(path),
                common_modules=mp.core.file_utils.discover_core_modules(path),
                actions_metadata={
                    a.file_name: a
                    for a in ActionMetadata.from_built_integration_path(path)
                },
                connectors_metadata={
                    c.file_name: c
                    for c in ConnectorMetadata.from_built_integration_path(path)
                },
                jobs_metadata={
                    j.file_name: j
                    for j in JobMetadata.from_built_integration_path(path)
                },
                widgets_metadata={
                    w.file_name: w
                    for w in WidgetMetadata.from_built_integration_path(path)
                },
            )
        except ValueError as e:
            msg: str = f"Failed to load integration {path}"
            raise ValueError(msg) from e

    @classmethod
    def from_non_built_path(cls, path: pathlib.Path) -> Integration:
        """Create the integration from a non-built integration's path.

        Args:
            path: the path to the "non-built" integration

        Returns:
            The integration objet

        Raises:
            ValueError: when the non-built integration failed to load

        """
        project_file_path: pathlib.Path = path / mp.core.constants.PROJECT_FILE
        file_content: str = project_file_path.read_text(encoding="utf-8")
        pyproject_toml: IntegrationPyProjectToml = tomllib.loads(file_content)  # type: ignore[assignment]
        try:
            integration_meta: IntegrationMetadata = (
                IntegrationMetadata.from_non_built_integration_path(path)
            )
            _update_integration_meta_form_pyproject(
                pyproject_toml=pyproject_toml,
                integration_meta=integration_meta,
            )
            return cls(
                identifier=integration_meta.identifier,
                metadata=integration_meta,
                release_notes=ReleaseNote.from_non_built_integration_path(path),
                custom_families=CustomFamily.from_non_built_integration_path(path),
                mapping_rules=MappingRule.from_non_built_integration_path(path),
                common_modules=mp.core.file_utils.discover_core_modules(path),
                actions_metadata={
                    a.file_name: a
                    for a in ActionMetadata.from_non_built_integration_path(path)
                },
                connectors_metadata={
                    c.file_name: c
                    for c in ConnectorMetadata.from_non_built_integration_path(path)
                },
                jobs_metadata={
                    j.file_name: j
                    for j in JobMetadata.from_non_built_integration_path(path)
                },
                widgets_metadata={
                    w.file_name: w
                    for w in WidgetMetadata.from_non_built_integration_path(path)
                },
            )

        except (KeyError, ValueError, tomllib.TOMLDecodeError) as e:
            msg: str = f"Failed to parse non built\n{pyproject_toml}"
            raise ValueError(msg) from e

    def _raise_error_if_no_ping_action(self) -> None:
        is_excluded_integration: bool = (
            self.identifier in mp.core.constants.EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING
        )
        if not is_excluded_integration and not self._has_ping_action():
            msg: str = f"{self.identifier} doesn't implement a 'ping' action"
            raise RuntimeError(msg)

    def _has_ping_action(self) -> bool:
        return any(name.lower() == "ping" for name in self.actions_metadata)

    def _raise_error_if_custom(self) -> None:
        """Raise an error if the integration is custom.

        Raises:
            RuntimeError: If the integration is custom.

        """
        if self.is_custom:
            msg: str = (
                f"{self.identifier} contains custom scripts:"
                f"\nIs the integration custom: {self.metadata.is_custom}"
                f"\nCustom actions: {', '.join(self.custom_actions) or None}"
                f"\nCustom connectors: {', '.join(self.custom_connectors) or None}"
                f"\nCustom jobs: {', '.join(self.custom_jobs) or None}"
            )
            raise RuntimeError(msg)

    def _raise_error_if_disabled(self) -> None:
        """Raise an error if the integration has disabled components.

        Raises:
            RuntimeError: If the integration has disabled components

        """
        if self.has_disabled_parts:
            msg: str = (
                f"{self.identifier} contains disabled scripts:"
                f"\nDisabled actions: {', '.join(self.disabled_actions) or None}"
                f"\nDisabled connectors: {', '.join(self.disabled_connectors) or None}"
                f"\nDisabled jobs: {', '.join(self.disabled_jobs) or None}"
            )
            raise RuntimeError(msg)

    @property
    def is_custom(self) -> bool:
        """Check whether the integration is custom.

        Returns:
            whether the integration has any custom components in it

        """
        return (
            self.metadata.is_custom
            or self.has_custom_actions
            or self.has_custom_connectors
            or self.has_custom_jobs
        )

    @property
    def has_disabled_parts(self) -> bool:
        """Check whether the integration is custom.

        Returns:
            whether the integration has any disabled components in it

        """
        return (
            self.has_disabled_actions
            or self.has_disabled_connectors
            or self.has_disabled_jobs
        )

    @property
    def has_custom_actions(self) -> bool:
        """Check whether any of the actions are custom.

        Returns:
            Whether the integration has any custom actions in it.

        """
        return any(a.is_custom for a in self.actions_metadata.values())

    @property
    def has_custom_connectors(self) -> bool:
        """Check whether any of the connectors are custom.

        Returns:
            Whether the integration has any custom connectors in it.

        """
        return any(c.is_custom for c in self.connectors_metadata.values())

    @property
    def has_custom_jobs(self) -> bool:
        """Check whether any of the jobs are custom.

        Returns:
            Whether the integration has any custom jobs in it.

        """
        return any(j.is_custom for j in self.jobs_metadata.values())

    @property
    def has_disabled_actions(self) -> bool:
        """Check whether any of the actions are disabled.

        Returns:
            Whether the integration has any disabled actions in it.

        """
        return any(not a.is_enabled for a in self.actions_metadata.values())

    @property
    def has_disabled_connectors(self) -> bool:
        """Check whether any of the connectors are disabled.

        Returns:
            Whether the integration has any disabled connectors in it.

        """
        return any(not c.is_enabled for c in self.connectors_metadata.values())

    @property
    def has_disabled_jobs(self) -> bool:
        """Check whether any of the jobs are disabled.

        Returns:
            Whether the integration has any disabled jobs in it.

        """
        return any(not j.is_enabled for j in self.jobs_metadata.values())

    @property
    def custom_actions(self) -> list[str]:
        """Get a list of custom actions.

        Returns:
            Custom action names

        """
        return [a.name for a in self.actions_metadata.values() if a.is_custom]

    @property
    def custom_connectors(self) -> list[str]:
        """Get a list of custom connectors.

        Returns:
            Custom connector names

        """
        return [c.name for c in self.connectors_metadata.values() if c.is_custom]

    @property
    def custom_jobs(self) -> list[str]:
        """Get a list of custom jobs.

        Returns:
            Custom job names

        """
        return [j.name for j in self.jobs_metadata.values() if j.is_custom]

    @property
    def disabled_actions(self) -> list[str]:
        """Get a list of disabled actions.

        Returns:
            Disabled action names

        """
        return [a.name for a in self.actions_metadata.values() if not a.is_enabled]

    @property
    def disabled_connectors(self) -> list[str]:
        """Get a list of disabled connectors.

        Returns:
            Disabled connector names

        """
        return [c.name for c in self.connectors_metadata.values() if not c.is_enabled]

    @property
    def disabled_jobs(self) -> list[str]:
        """Get a list of disabled jobs.

        Returns:
            Disabled job names

        """
        return [j.name for j in self.jobs_metadata.values() if not j.is_enabled]

    def to_built(self) -> BuiltIntegration:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" representation of the object.

        """
        return BuiltIntegration(
            metadata=self.metadata.to_built(),
            release_notes=[rn.to_built() for rn in self.release_notes],
            custom_families=[cf.to_built() for cf in self.custom_families],
            mapping_rules=[mr.to_built() for mr in self.mapping_rules],
            common_modules=self.common_modules,
            actions={
                name: metadata.to_built()
                for name, metadata in self.actions_metadata.items()
            },
            connectors={
                name: metadata.to_built()
                for name, metadata in self.connectors_metadata.items()
            },
            jobs={
                name: metadata.to_built()
                for name, metadata in self.jobs_metadata.items()
            },
            widgets={
                name: metadata.to_built()
                for name, metadata in self.widgets_metadata.items()
            },
        )

    def to_non_built(self) -> NonBuiltIntegration:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" representation of the object

        """
        return NonBuiltIntegration(
            metadata=self.metadata.to_non_built(),
            release_notes=[rn.to_non_built() for rn in self.release_notes],
            custom_families=[cf.to_non_built() for cf in self.custom_families],
            mapping_rules=[mr.to_non_built() for mr in self.mapping_rules],
            common_modules=self.common_modules,
            actions={
                name: metadata.to_non_built()
                for name, metadata in self.actions_metadata.items()
            },
            connectors={
                name: metadata.to_non_built()
                for name, metadata in self.connectors_metadata.items()
            },
            jobs={
                name: metadata.to_non_built()
                for name, metadata in self.jobs_metadata.items()
            },
            widgets={
                name: metadata.to_non_built()
                for name, metadata in self.widgets_metadata.items()
            },
        )

    def to_built_full_details(self) -> BuiltFullDetails:
        """Turn the integration into a `full-details` JSON form.

        Returns:
            The `full-details` JSON form of the integration.

        """
        return BuiltFullDetails(
            Identifier=self.metadata.identifier,
            PackageName=self.metadata.name,
            DisplayName=self.metadata.name,
            Description=self.metadata.description,
            DocumentationLink=(
                str(self.metadata.documentation_link)
                if self.metadata.documentation_link is not None
                else None
            ),
            MinimumSystemVersion=float(self.metadata.minimum_system_version),
            IntegrationProperties=[p.to_built() for p in self.metadata.parameters],
            Actions=[am.name for am in self.actions_metadata.values()],
            Jobs=[jm.name for jm in self.jobs_metadata.values()],
            Connectors=[cm.name for cm in self.connectors_metadata.values()],
            Managers=self.common_modules,
            CustomFamilies=[cf.family for cf in self.custom_families],
            MappingRules=["Default mapping rules"] if self.mapping_rules else [],
            Widgets=[wm.title for wm in self.widgets_metadata.values()],
            Version=float(self.metadata.version),
            IsCustom=False,
            ExampleUseCases=[],
            ReleaseNotes=self._get_full_details_release_notes(),
        )

    def _get_full_details_release_notes(self) -> list[FullDetailsReleaseNoteJson]:
        version_to_rns: itertools.groupby[float, ReleaseNote] = itertools.groupby(
            self.release_notes,
            lambda rn: float(rn.version),
        )
        release_notes: list[FullDetailsReleaseNoteJson] = []
        for version, items in version_to_rns:
            # casting done to prevent generator exhaustion after the first iteration
            rns: list[ReleaseNote] = list(items)
            max_publish_time: int = max(
                rn.publish_time if rn.publish_time is not None else 0 for rn in rns
            )
            rn_object: FullDetailsReleaseNoteJson = {
                "Version": version,
                "Items": [rn.description for rn in rns],
                "PublishTimeUnixTime": max_publish_time * mp.core.constants.MS_IN_SEC,
            }
            release_notes.append(rn_object)

        return release_notes


def _update_integration_meta_form_pyproject(
    pyproject_toml: IntegrationPyProjectToml,
    integration_meta: IntegrationMetadata,
) -> None:
    """Update the integration's metadata based on changes in the project file.

    Args:
        pyproject_toml: the integration's project file
        integration_meta: the integration's metadata

    """
    pyv: str = mp.core.utils.get_python_version_from_version_string(
        pyproject_toml["project"]["requires-python"],
    )
    integration_meta.python_version = PythonVersion.from_string(pyv)
    integration_meta.description = pyproject_toml["project"]["description"]
    integration_meta.version = decimal.Decimal(
        float(pyproject_toml["project"]["version"])
    )
