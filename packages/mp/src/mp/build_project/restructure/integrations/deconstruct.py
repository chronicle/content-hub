"""Module for deconstructing a built integration into its source structure.

This module defines a class, `DeconstructIntegration`, which takes a built
integration and reorganizes its files and metadata into a structure
suitable for development and modification. This involves separating
scripts, definitions, and other related files into designated directories.
"""

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
import datetime
import io
import shutil
import tomllib
from typing import TYPE_CHECKING, Any, TypeAlias

import rich
import toml

import mp.core.constants
import mp.core.file_utils
import mp.core.unix
import mp.core.utils
from mp.build_project.restructure.integrations.deconstruct_dependencies import (
    Dependencies,
    DependencyDeconstructor,
)
from mp.core import code_manipulation
from mp.core.constants import IMAGE_FILE, LOGO_FILE, RESOURCES_DIR
from mp.core.data_models.common.release_notes.metadata import NonBuiltReleaseNote
from mp.core.data_models.integrations.action.metadata import ActionMetadata
from mp.core.data_models.integrations.action_widget.metadata import ActionWidgetMetadata
from mp.core.data_models.integrations.connector.metadata import ConnectorMetadata
from mp.core.data_models.integrations.integration_meta.metadata import (
    IntegrationMetadata,
    PythonVersion,
)
from mp.core.data_models.integrations.job.metadata import JobMetadata

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping
    from pathlib import Path

    import libcst as cst

    from mp.core.data_models.integrations.action.dynamic_results_metadata import (
        DynamicResultsMetadata,
    )
    from mp.core.data_models.integrations.custom_families.metadata import NonBuiltCustomFamily
    from mp.core.data_models.integrations.integration import Integration
    from mp.core.data_models.integrations.mapping_rules.metadata import NonBuiltMappingRule

_ValidMetadata: TypeAlias = ActionMetadata | ConnectorMetadata | JobMetadata | ActionWidgetMetadata


def _update_pyproject_from_integration_meta(
    pyproject_toml: MutableMapping[str, Any],
    integration_meta: IntegrationMetadata,
) -> None:
    py_version: str = PythonVersion(integration_meta.python_version).to_string()
    pyproject_toml["project"].update(
        {
            "name": integration_meta.identifier.replace(" ", "-"),
            "description": integration_meta.description,
            "version": str(float(integration_meta.version)),
            "requires-python": f">={py_version}",
        },
    )


@dataclasses.dataclass(slots=True, frozen=True)
class DeconstructIntegration:
    path: Path
    out_path: Path
    integration: Integration

    @property
    def core_module_names(self) -> set[str]:
        """Extract the names of manager modules from the built integration path."""
        managers_path = self.path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
        return {f.stem for f in managers_path.glob("*.py") if f.stem != "__init__"}

    def initiate_project(self) -> None:
        """Initialize a new python project.

        Initializes a project by setting up a Python environment, updating the
        project configuration, and optionally adding dependencies based on a
        'requirements.txt' file.

        """
        result = DependencyDeconstructor(self.path).get_dependencies()

        mp.core.unix.init_python_project_if_not_exists(self.out_path)
        self.update_pyproject(placeholders=result.placeholders)

        rich.print(f"Adding dependencies to {mp.core.constants.PROJECT_FILE}")
        try:
            mp.core.unix.add_dependencies_to_toml(
                project_path=self.out_path,
                deps_to_add=result.dependencies.dependencies,
                dev_deps_to_add=result.dependencies.dev_dependencies,
            )

        except mp.core.unix.FatalCommandError as e:
            rich.print(f"Failed to install dependencies: {e}")

    def update_pyproject(self, placeholders: Dependencies | None = None) -> None:
        """Update an integration's pyproject.toml file from its definition file."""
        pyproject_toml: Path = self.out_path / mp.core.constants.PROJECT_FILE
        toml_content: MutableMapping[str, Any] = tomllib.loads(
            pyproject_toml.read_text(encoding="utf-8"),
        )
        _update_pyproject_from_integration_meta(toml_content, self.integration.metadata)

        buffer = io.StringIO()
        buffer.write(toml.dumps(toml_content))

        if placeholders and (placeholders.dependencies or placeholders.dev_dependencies):
            for dep in placeholders.dependencies:
                buffer.write(
                    f"\n# TODO: Failed to automatically add the following dependency. "
                    f"Please add it manually: {dep}\n",
                )
            for dep in placeholders.dev_dependencies:
                buffer.write(
                    f"\n# TODO: Failed to automatically add the following dev-dependency. "
                    f"Please add it manually: {dep}\n",
                )

        pyproject_toml.write_text(buffer.getvalue(), encoding="utf-8")
        self._copy_lock_file()

    def _copy_lock_file(self) -> None:
        lock_file: Path = self.path / mp.core.constants.LOCK_FILE
        out_lock_file: Path = self.out_path / mp.core.constants.LOCK_FILE
        if lock_file.exists() and not out_lock_file.exists():
            shutil.copyfile(lock_file, out_lock_file)

    def deconstruct_integration_files(self) -> None:
        """Deconstruct an integration's code to its "out" path."""
        self._create_resource_files()
        self._create_definition_file()
        self._create_release_notes()
        self._create_custom_families()
        self._create_mapping_rules()
        self._create_scripts_dirs()
        self._create_package_file()
        self._create_python_version_file()

    def _create_resource_files(self) -> None:
        """Create the image files in the resources directory."""
        resources_dir: Path = self.out_path / RESOURCES_DIR
        resources_dir.mkdir(exist_ok=True)

        self._create_png_image(resources_dir)
        self._create_svg_logo(resources_dir)

    def _create_png_image(self, resources_dir: Path) -> None:
        if self.integration.metadata.image_base64:
            mp.core.file_utils.base64_to_png_file(
                self.integration.metadata.image_base64, resources_dir / IMAGE_FILE
            )

    def _create_svg_logo(self, resources_dir: Path) -> None:
        if self.integration.metadata.svg_logo:
            mp.core.file_utils.text_to_svg_file(
                self.integration.metadata.svg_logo, resources_dir / LOGO_FILE
            )

    def _create_actions_json_example_files(self) -> None:
        resources_dir: Path = self.out_path / RESOURCES_DIR
        for action_name, action_metadata in self.integration.actions_metadata.items():
            drms: list[DynamicResultsMetadata] = action_metadata.dynamic_results_metadata
            for drm in drms:
                if not drm.result_example:
                    continue

                json_file_name: str = (
                    f"{mp.core.utils.str_to_snake_case(action_name)}_{drm.result_name}_example.json"
                )
                json_file_path: Path = resources_dir / json_file_name
                mp.core.file_utils.write_str_to_json_file(json_file_path, drm.result_example)

    def _create_definition_file(self) -> None:
        def_file: Path = self.out_path / mp.core.constants.DEFINITION_FILE
        mp.core.file_utils.write_yaml_to_file(
            content=self.integration.metadata.to_non_built(),
            path=def_file,
        )

    def _create_python_version_file(self) -> None:
        out_python_version_file: Path = self.out_path / mp.core.constants.PYTHON_VERSION_FILE
        python_version_file: Path = self.path / mp.core.constants.PYTHON_VERSION_FILE

        python_version: str = ""
        if python_version_file.is_file():
            python_version = python_version_file.read_text(encoding="utf-8")
        if not python_version:
            python_version = self.integration.metadata.python_version.to_string()

        out_python_version_file.write_text(python_version, encoding="utf-8")

    def _create_release_notes(self) -> None:
        rn: Path = self.out_path / mp.core.constants.RELEASE_NOTES_FILE
        if self.integration.release_notes:
            mp.core.file_utils.write_yaml_to_file(
                content=[r.to_non_built() for r in self.integration.release_notes],
                path=rn,
            )
        else:
            mp.core.file_utils.write_yaml_to_file(
                content=[
                    NonBuiltReleaseNote(
                        description="",
                        integration_version=float(self.integration.metadata.version),
                        item_name=self.integration.metadata.identifier,
                        item_type="Integration",
                        publish_time=str(datetime.datetime.now(datetime.UTC).date()),
                        ticket_number="No ticket",
                    )
                ],
                path=rn,
            )

    def _create_custom_families(self) -> None:
        cf: Path = self.out_path / mp.core.constants.CUSTOM_FAMILIES_FILE
        families: list[NonBuiltCustomFamily] = [
            c.to_non_built() for c in self.integration.custom_families
        ]
        if families:
            mp.core.file_utils.write_yaml_to_file(families, cf)

    def _create_mapping_rules(self) -> None:
        mr: Path = self.out_path / mp.core.constants.MAPPING_RULES_FILE
        mapping: list[NonBuiltMappingRule] = [
            m.to_non_built() for m in self.integration.mapping_rules
        ]
        if mapping:
            mp.core.file_utils.write_yaml_to_file(mapping, mr)

    def _create_scripts_dirs(self) -> None:
        self._create_actions_json_example_files()
        self._create_scripts_dir(
            repo_dir=mp.core.constants.OUT_ACTION_SCRIPTS_DIR,
            out_dir=mp.core.constants.ACTIONS_DIR,
            metadata=self.integration.actions_metadata,
        )
        self._create_scripts_dir(
            repo_dir=mp.core.constants.OUT_CONNECTOR_SCRIPTS_DIR,
            out_dir=mp.core.constants.CONNECTORS_DIR,
            metadata=self.integration.connectors_metadata,
        )
        self._create_scripts_dir(
            repo_dir=mp.core.constants.OUT_JOB_SCRIPTS_DIR,
            out_dir=mp.core.constants.JOBS_DIR,
            metadata=self.integration.jobs_metadata,
        )
        self._create_scripts_dir(
            repo_dir=mp.core.constants.OUT_WIDGET_SCRIPTS_DIR,
            out_dir=mp.core.constants.WIDGETS_DIR,
            metadata=self.integration.widgets_metadata,
            is_python_dir=False,
        )
        self._create_scripts_dir(
            repo_dir=mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR,
            out_dir=mp.core.constants.CORE_SCRIPTS_DIR,
            metadata=None,
        )

    def _create_scripts_dir(
        self,
        repo_dir: str,
        out_dir: str,
        metadata: Mapping[str, _ValidMetadata] | None,
        *,
        is_python_dir: bool = True,
    ) -> None:
        old_path: Path = self.path / repo_dir
        if not old_path.exists():
            return

        new_path: Path = self.out_path / out_dir
        new_path.mkdir(exist_ok=True)
        for file in old_path.iterdir():
            if file.is_file():
                shutil.copy(file, new_path)
                copied_file: Path = new_path / file.name
                copied_file.rename(copied_file.parent / copied_file.name)
                self._transform_imports(copied_file, out_dir)

        if metadata is not None:
            _write_definitions(new_path, metadata)

        if is_python_dir:
            (new_path / mp.core.constants.PACKAGE_FILE).touch()

    def _transform_imports(self, file_path: Path, out_dir: str) -> None:
        if file_path.suffix != ".py":
            return

        transformers: list[cst.CSTTransformer] = [
            code_manipulation.FutureAnnotationsTransformer(),
            code_manipulation.SdkImportTransformer(),
        ]

        if out_dir != mp.core.constants.CORE_SCRIPTS_DIR:
            transformers.append(
                code_manipulation.CorePackageImportTransformer(self.core_module_names)
            )
        else:
            transformers.append(
                code_manipulation.CorePackageInternalImportTransformer(
                    self.core_module_names, file_path.stem
                )
            )

        original_content: str = file_path.read_text(encoding="utf-8")
        transformed_content: str = code_manipulation.apply_transformers(
            original_content, transformers
        )
        file_path.write_text(transformed_content, encoding="utf-8")

    def _create_package_file(self) -> None:
        (self.out_path / mp.core.constants.PACKAGE_FILE).touch()


def _write_definitions(path: Path, component: Mapping[str, _ValidMetadata]) -> None:
    for file_name, metadata in component.items():
        name: str = f"{file_name}{mp.core.constants.YAML_SUFFIX}"
        mp.core.file_utils.write_yaml_to_file(metadata.to_non_built(), path / name)
