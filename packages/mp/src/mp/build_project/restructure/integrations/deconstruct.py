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
import shutil
import tomllib
from typing import TYPE_CHECKING, Any, TypeAlias

import libcst as cst
import rich
import toml

import mp.core.constants
import mp.core.file_utils
import mp.core.unix
from mp.core.constants import IMAGE_FILE, LOGO_FILE, RESOURCES_DIR, SDK_MODULES
import mp.core.utils
from mp.core.constants import IMAGE_FILE, LOGO_FILE, RESOURCES_DIR
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

    from mp.core.data_models.integrations.action.dynamic_results_metadata import (
        DynamicResultsMetadata,
    )
    from mp.core.data_models.integrations.custom_families.metadata import NonBuiltCustomFamily
    from mp.core.data_models.integrations.integration import Integration
    from mp.core.data_models.integrations.mapping_rules.metadata import NonBuiltMappingRule

_ValidMetadata: TypeAlias = ActionMetadata | ConnectorMetadata | JobMetadata | ActionWidgetMetadata

SDK_PREFIX = f"{mp.core.constants.SDK_PACKAGE_NAME}."


def _create_prefixed_module(full_module_name: str, prefix: str) -> cst.BaseExpression:
    new_module_name: str = prefix + full_module_name
    return cst.parse_expression(new_module_name)


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


class SdkImportTransformer(cst.CSTTransformer):
    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:  # noqa: N802, PLR6301
        """Ensure `from __future__ import annotations` is present at the top of the module.

        Returns:
            The updated module with `from __future__ import annotations` at the top.

        """
        if not original_node.body:
            return updated_node
        import_annotations: cst.SimpleStatementLine = cst.parse_statement(
            "from __future__ import annotations"
        )
        new_body: list[cst.SimpleStatementLine] = [
            import_annotations,
            cst.EmptyLine(),
            *updated_node.body,
        ]
        return updated_node.with_changes(body=new_body)

    def leave_ImportFrom(  # noqa: N802, PLR6301
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for SDK modules.

        Returns:
            The updated `ImportFrom` node with SDK modules prefixed.

        """
        full_module_name: str = cst.helpers.get_full_name_for_node(original_node.module)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in SDK_MODULES and not full_module_name.startswith(SDK_PREFIX):
            prefixed_module: cst.BaseExpression = _create_prefixed_module(
                full_module_name, SDK_PREFIX
            )
            return updated_node.with_changes(module=prefixed_module)

        return updated_node

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:  # noqa: N802, PLR6301
        """Transform `import <module>` statements for SDK modules.

        Returns:
            The updated `Import` node with SDK modules prefixed.

        """
        full_module_name: str = cst.helpers.get_full_name_for_node(original_node.names[0].name)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in SDK_MODULES and not full_module_name.startswith(SDK_PREFIX):
            prefixed_module: cst.BaseExpression = _create_prefixed_module(
                full_module_name, SDK_PREFIX
            )
            return updated_node.with_changes(names=[cst.ImportAlias(name=prefixed_module)])

        return updated_node


class ManagerImportTransformer(cst.CSTTransformer):
    def __init__(self, manager_names: set[str]) -> None:
        self.manager_names: set[str] = manager_names

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for manager modules.

        Returns:
            The updated `ImportFrom` node with manager modules transformed to relative imports.

        """
        if original_node.relative:
            return updated_node

        full_module_name: str = cst.helpers.get_full_name_for_node(original_node.module)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in self.manager_names:
            prefixed_module: cst.BaseExpression = _create_prefixed_module(full_module_name, "core.")
            return updated_node.with_changes(
                module=prefixed_module, relative=(cst.Dot(), cst.Dot())
            )

        return updated_node

    def leave_Import(  # noqa: N802
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.ImportFrom | cst.Import:
        """Transform `import <module>` statements for manager modules.

        Returns:
            The updated `Import` or a new `ImportFrom` node for manager modules.

        """
        full_module_name: str = cst.helpers.get_full_name_for_node(original_node.names[0].name)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in self.manager_names:
            return cst.ImportFrom(
                module=cst.Name(value="core"),
                names=[cst.ImportAlias(name=cst.Name(value=first_module_part))],
                relative=(cst.Dot(), cst.Dot()),
            )

        return updated_node


def apply_transformers(content: str, transformers: list[cst.CSTTransformer]) -> str:
    """Parse code once and apply a list of transformers sequentially.

    Returns:
        The transformed code as a string, or the original content if a syntax error occurs.

    """
    try:
        tree = cst.parse_module(content)
        for transformer in transformers:
            tree = tree.visit(transformer)
    except cst.ParserSyntaxError:
        return content
    else:
        return tree.code


@dataclasses.dataclass(slots=True, frozen=True)
class DeconstructIntegration:
    path: Path
    out_path: Path
    integration: Integration

    @property
    def manager_names(self) -> set[str]:
        """Extract the names of manager modules from the built integration path."""
        managers_path = self.path / mp.core.constants.OUT_MANAGERS_SCRIPTS_DIR
        return {f.stem for f in managers_path.glob("*.py") if f.stem != "__init__"}

    def initiate_project(self) -> None:
        """Initialize a new python project.

        Initializes a project by setting up a Python environment, updating the
        project configuration, and optionally adding dependencies based on a
        'requirements.txt' file.

        """
        mp.core.unix.init_python_project_if_not_exists(self.out_path)
        self.update_pyproject()
        requirements: Path = self.path / mp.core.constants.REQUIREMENTS_FILE
        if requirements.exists():
            try:
                rich.print(f"Adding requirements to {mp.core.constants.PROJECT_FILE}")
                mp.core.unix.add_dependencies_to_toml(
                    project_path=self.out_path,
                    requirements_path=requirements,
                )
            except mp.core.unix.FatalCommandError as e:
                rich.print(f"Failed to install dependencies from requirements: {e}")

    def update_pyproject(self) -> None:
        """Update an integration's pyproject.toml file from its definition file."""
        pyproject_toml: Path = self.out_path / mp.core.constants.PROJECT_FILE
        toml_content: MutableMapping[str, Any] = tomllib.loads(
            pyproject_toml.read_text(encoding="utf-8"),
        )
        _update_pyproject_from_integration_meta(toml_content, self.integration.metadata)
        pyproject_toml.write_text(toml.dumps(toml_content), encoding="utf-8")
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
        mp.core.file_utils.write_yaml_to_file(
            content=[r.to_non_built() for r in self.integration.release_notes],
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

    def _transform_imports(self, file_path: Path, out_dir: str) -> None:
        if file_path.suffix != ".py":
            return

        transformers: list[cst.CSTTransformer] = [SdkImportTransformer()]

        if out_dir != mp.core.constants.CORE_SCRIPTS_DIR:
            transformers.append(ManagerImportTransformer(self.manager_names))

        original_content: str = file_path.read_text(encoding="utf-8")
        transformed_content: str = apply_transformers(original_content, transformers)
        file_path.write_text(transformed_content, encoding="utf-8")

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

    def _create_package_file(self) -> None:
        (self.out_path / mp.core.constants.PACKAGE_FILE).touch()


def _write_definitions(path: Path, component: Mapping[str, _ValidMetadata]) -> None:
    for file_name, metadata in component.items():
        name: str = f"{file_name}{mp.core.constants.DEF_FILE_SUFFIX}"
        mp.core.file_utils.write_yaml_to_file(metadata.to_non_built(), path / name)
