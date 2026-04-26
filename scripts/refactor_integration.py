# Copyright 2026 Google LLC
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

import argparse
import json
import logging
import os
import shutil
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union, cast

import libcst as cst
import mp.core.file_utils
import toml
import yaml
from mp.build_project.integrations_repo import IntegrationsRepo
from mp.core.config import get_local_packages_path, get_marketplace_path
from mp.core.constants import SDK_MODULES
from mp.core.unix import add_dependencies_to_toml
from mp.core.utils.common import str_to_snake_case
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

# --- Global Configuration Constants ---

WIDGETS_DIR = "Widgets"
PYPROJECT_TOML = "pyproject.toml"
PYTHONPATH_FILE = "pythonpath.txt"
RELEASE_NOTES_FILE = "release_notes.yaml"
RUFF_TOML = "ruff.toml"

INTEGRATIONS_PATH_MAPPING = {
    "ActionsScripts": "actions",
    "JobsScrips": "jobs",
    "Managers": "core",
    "ConnectorScripts": "connectors",
    "ConnectorsScripts": "connectors",
}

TESTS_PATH_MAPPING = {
    "session": "requests.session",
    "response": "requests.response",
}

TESTS_FUNCTIONS_MAPPING = {"get_json_file_content": "get_def_file_content"}

MIGRATION_RELEASE_NOTE_TEMPLATE = {
    "description": (
        "Integration - Source code for the integration is now available publicly on "
        "Github. Link to repo: https://github.com/chronicle/content-hub"
    ),
    "integration_version": "{integration_version}",
    "item_name": "{item_name}",
    "item_type": "Integration",
    "publish_time": "{publish_time}",
    "new": False,
    "regressive": False,
    "deprecated": False,
    "removed": False,
    "ticket_number": "495762513",
}

NEW_IMPORT_TEST_CONTENT = (
    "from __future__ import annotations\n\n"
    "from integration_testing.default_tests.import_test import import_all_integration_modules\n\n"
    "from .. import common\n\n\n"
    "def test_imports() -> None:\n"
    "    import_all_integration_modules(common.INTEGRATION_PATH)\n"
)

LOCAL_IMPORT_TEST_CONTENT = (
    "from __future__ import annotations\n\n"
    "import importlib\n"
    "import pathlib\n\n"
    "from .. import common\n\n\n"
    'VALID_SUFFIXES = (".py",)\n\n\n'
    "def import_all_integration_modules(integration: pathlib.Path) -> None:\n"
    "    if not integration.exists():\n"
    '        msg: str = f"Cannot find integration {integration.name}"\n'
    "        raise AssertionError(msg)\n\n"
    "    imports: list[str] = _get_integration_modules_import_strings(integration)\n"
    "    for import_ in imports:\n"
    "        importlib.import_module(import_)\n\n\n"
    "def _get_integration_modules_import_strings(integration: pathlib.Path) -> list[str]:\n"
    "    results: list[str] = []\n"
    "    for package in integration.iterdir():\n"
    "        if not package.is_dir():\n"
    "            continue\n\n"
    "        for module in package.iterdir():\n"
    "            if not module.is_file() or module.suffix not in VALID_SUFFIXES:\n"
    "                continue\n\n"
    "            import_: str = _get_import_string(integration.stem, package.stem, module.stem)\n"
    "            results.append(import_)\n\n"
    "    return results\n\n\n"
    "def _get_import_string(integration: str, package: str, module: str) -> str:\n"
    '    return f"{integration}.{package}.{module}"\n\n\n'
    "def test_imports() -> None:\n"
    "    import_all_integration_modules(common.INTEGRATION_PATH)\n"
)

# Initialize Rich Console and Logging
console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)],
)
logger = logging.getLogger("refactor_integration")


# --- Utility Functions ---


def _capitalize_first_letter(s: str) -> str:
    """Capitalizes the first letter of a string, leaving the rest unchanged."""
    return s[:1].upper() + s[1:] if s else s


def _get_module_path_str(module_node: Optional[cst.BaseExpression]) -> str:
    """Recursively reconstructs the full dotted path from a CST node."""
    if module_node is None:
        return ""
    if isinstance(module_node, cst.Name):
        return module_node.value
    if isinstance(module_node, cst.Attribute):
        return f"{_get_module_path_str(module_node.value)}.{module_node.attr.value}"
    return ""


def _remap_sdk_path(path: str) -> str:
    """Adds 'soar_sdk.' prefix to modules from the SDK."""
    if path and path.split(".")[0] in SDK_MODULES:
        return f"soar_sdk.{path}"
    return path


# --- CST Transformers ---


class SDKInstanceTransformer(cst.CSTTransformer):
    """Replaces strict isinstance checks on SDK objects with hasattr checks."""

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> Union[cst.Call, cst.BaseExpression]:
        if not (isinstance(updated_node.func, cst.Name) and updated_node.func.value == "isinstance"):
            return updated_node

        if len(updated_node.args) < 2:
            return updated_node

        obj = updated_node.args[0].value
        type_arg = updated_node.args[1].value

        sdk_classes = {"SiemplifyAction", "SiemplifyConnectorExecution", "SiemplifyJob", "Siemplify"}

        type_names = []
        if isinstance(type_arg, cst.Name):
            type_names = [type_arg.value]
        elif isinstance(type_arg, cst.Tuple):
            type_names = [e.value.value for e in type_arg.elements if isinstance(e.value, cst.Name)]

        if not any(tn in sdk_classes for tn in type_names):
            return updated_node

        logger.info(f"Found SDK isinstance check: {type_names}")
        obj_code = cst.Module([]).code_for_node(obj).strip()
        logger.info(f"Object code: {obj_code}")

        # If any of the classes in the check are SDK classes, use hasattr
        if "SiemplifyAction" in type_names or "Siemplify" in type_names:
            res = cst.parse_expression(f"hasattr({obj_code}, 'get_configuration')")
            logger.info(f"Transformed to: {res.code if hasattr(res, 'code') else 'res'}")
            return res
        elif "SiemplifyConnectorExecution" in type_names or "SiemplifyJob" in type_names:
            return cst.parse_expression(f"hasattr({obj_code}, 'parameters')")
        else:
            # Fallback for general SDK check
            return cst.parse_expression(
                f"(hasattr({obj_code}, 'get_configuration') or hasattr({obj_code}, 'parameters'))"
            )


class ImportTransformer(cst.CSTTransformer):
    """Handles remapping of imports during integration refactoring."""

    def __init__(self, integration_name: str, deconstructed_name: str):
        super().__init__()
        self.integration_name = integration_name
        self.deconstructed_name = deconstructed_name
        self.needs_abc_import = False
        self.has_abc_import = False

    def _remap_integration_path(self, path: str) -> str:
        # Handle Integrations.*
        prefix = f"Integrations.{self.integration_name}"
        if path.startswith(prefix):
            parts = path[len(prefix) :].strip(".").split(".")
            if parts and parts[0] in INTEGRATIONS_PATH_MAPPING:
                parts[0] = INTEGRATIONS_PATH_MAPPING[parts[0]]
            return ".".join(filter(None, [self.deconstructed_name] + parts))

        # Handle absolute imports that might have been partially refactored
        if path.startswith(self.integration_name) and not path.startswith(f"{self.deconstructed_name}"):
            return path.replace(self.integration_name, self.deconstructed_name, 1)

        return path

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if isinstance(alias, cst.ImportAlias) and alias.name.value == "abc":
                self.has_abc_import = True

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:
        new_aliases = []
        for alias in updated_node.names:
            if isinstance(alias, cst.ImportAlias):
                old_path = _get_module_path_str(alias.name)
                remapped_path = self._remap_integration_path(old_path)
                new_path = _remap_sdk_path(remapped_path)
                logger.debug(f"Remapped import: {old_path} -> {new_path}")
                new_aliases.append(alias.with_changes(name=cst.parse_expression(new_path)))
            else:
                new_aliases.append(alias)
        return updated_node.with_changes(names=tuple(new_aliases))

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[cst.ImportFrom, cst.RemovalSentinel]:
        if updated_node.module is None:
            return updated_node

        module_path = _get_module_path_str(updated_node.module)

        if "Tests.mocks.product" in module_path:
            self.needs_abc_import = True
            logger.debug(f"Removed mock product import from module: {module_path}")
            return cst.RemoveFromParent()

        remapped_path = _remap_sdk_path(module_path)

        if module_path.startswith(f"Integrations.{self.integration_name}"):
            remapped = self._remap_integration_path(remapped_path)
            logger.debug(f"Remapped integration import from: {module_path} -> {remapped}")
            return updated_node.with_changes(
                module=cst.parse_expression(remapped),
                relative=(),
            )

        test_prefix = f"Tests.integrations.{self.integration_name}"
        if module_path.startswith(test_prefix):
            new_module = module_path.replace(test_prefix, f"{self.deconstructed_name}.tests", 1)
            logger.debug(f"Remapped test import from: {module_path} -> {new_module}")
            return updated_node.with_changes(
                module=cst.parse_expression(new_module),
                relative=(),
            )

        if "Tests.mocks" in module_path:
            return self._handle_mock_utility_imports(updated_node, module_path)

        if remapped_path != module_path:
            return updated_node.with_changes(module=cst.parse_expression(remapped_path), relative=())

        return updated_node

    def _handle_mock_utility_imports(self, node: cst.ImportFrom, path: str) -> cst.ImportFrom:
        new_path = path.replace("Tests.mocks", "integration_testing")
        for old, new in TESTS_PATH_MAPPING.items():
            new_path = new_path.replace(old, new)

        logger.debug(f"Remapped mock utility import path: {path} -> {new_path}")

        if isinstance(node.names, cst.ImportStar):
            return node.with_changes(module=cst.parse_expression(new_path), relative=())

        new_names = []
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                new_names.append(alias)
                continue
            name = alias.name.value
            if name in TESTS_FUNCTIONS_MAPPING:
                new_name = cst.Name(TESTS_FUNCTIONS_MAPPING[name])
                new_names.append(alias.with_changes(name=new_name))
            elif name in ("set_is_first_run_to", "set_is_test_run_to"):
                new_names.extend([
                    cst.ImportAlias(name=cst.Name(f"{name}_true")),
                    cst.ImportAlias(name=cst.Name(f"{name}_false")),
                ])
            else:
                new_names.append(alias)
        return node.with_changes(module=cst.parse_expression(new_path), relative=(), names=tuple(new_names))

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        func = updated_node.func
        if isinstance(func, cst.Name) and func.value in (
            "set_is_first_run_to",
            "set_is_test_run_to",
        ):
            if updated_node.args:
                val = updated_node.args[0].value
                if isinstance(val, cst.Name) and val.value in ("True", "False"):
                    new_func_name = f"{func.value}_{val.value.lower()}"
                    return updated_node.with_changes(func=cst.Name(new_func_name), args=[])

        if isinstance(func, (cst.Name, cst.Attribute)):
            name_node = func.attr if isinstance(func, cst.Attribute) else func
            if name_node.value in TESTS_FUNCTIONS_MAPPING:
                new_name = cst.Name(TESTS_FUNCTIONS_MAPPING[name_node.value])
                if isinstance(func, cst.Attribute):
                    return updated_node.with_changes(func=func.with_changes(attr=new_name))
                return updated_node.with_changes(func=new_name)
        return updated_node

    def leave_SimpleString(self, original_node: cst.SimpleString, updated_node: cst.SimpleString) -> cst.SimpleString:
        raw_val = updated_node.value.strip("'\"")
        quote = updated_node.value[0]

        if raw_val.startswith(f"Integrations.{self.integration_name}"):
            remapped = self._remap_integration_path(raw_val)
            logger.debug(f"Remapped string literal: {raw_val} -> {remapped}")
            return updated_node.with_changes(value=f"{quote}{remapped}{quote}")

        test_prefix = f"Tests.integrations.{self.integration_name}"
        if raw_val.startswith(test_prefix):
            replaced = raw_val.replace(test_prefix, "tests", 1)
            logger.debug(f"Remapped test string literal: {raw_val} -> {replaced}")
            return updated_node.with_changes(value=f"{quote}{replaced}{quote}")

        if raw_val.endswith((".actiondef", ".connectordef", ".jobdef")):
            new_val = (
                raw_val.replace(".actiondef", ".yaml").replace(".connectordef", ".yaml").replace(".jobdef", ".yaml")
            )
            return updated_node.with_changes(value=f"{quote}{new_val}{quote}")
        return updated_node

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        new_bases = [
            b.with_changes(value=cst.parse_expression("abc.ABC"))
            if (isinstance(b.value, cst.Name) and b.value.value == "MockProduct")
            else b
            for b in updated_node.bases
        ]
        if any(b != old_b for b, old_b in zip(new_bases, updated_node.bases)):
            self.needs_abc_import = True
            return updated_node.with_changes(bases=new_bases)
        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self.needs_abc_import and not self.has_abc_import:
            new_body = list(updated_node.body)
            # Find where to insert (after future, before others)
            insert_idx = 0
            for i, stmt in enumerate(new_body):
                if (
                    isinstance(stmt, cst.SimpleStatementLine)
                    and isinstance(stmt.body[0], cst.ImportFrom)
                    and stmt.body[0].module.value == "__future__"
                ):
                    insert_idx = i + 1
                    break

            new_body.insert(insert_idx, cast(cst.SimpleStatementLine, cst.parse_statement("import abc")))
            return updated_node.with_changes(body=tuple(new_body))
        return updated_node

    @staticmethod
    def _is_future(node: Any) -> bool:
        return (
            isinstance(node, cst.SimpleStatementLine)
            and isinstance(node.body[0], cst.ImportFrom)
            and getattr(node.body[0].module, "value", "") == "__future__"
        )


class UpsertIntegrationPathTransformer(cst.CSTTransformer):
    """Ensures necessary imports, INTEGRATION_PATH, and CONFIG exist in common.py."""

    def __init__(self):
        super().__init__()
        self.has_future = False
        self.has_pathlib = False
        self.has_json = False
        self.has_int_path = False
        self.has_config_path = False
        self.has_config = False
        self.has_get_def = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module and isinstance(node.module, cst.Name) and node.module.value == "__future__":
            if any(isinstance(a, cst.ImportAlias) and a.name.value == "annotations" for a in node.names):
                self.has_future = True
        if node.module and isinstance(node.module, cst.Name) and node.module.value == "integration_testing.common":
            if any(isinstance(a, cst.ImportAlias) and a.name.value == "get_def_file_content" for a in node.names):
                self.has_get_def = True

    def visit_Import(self, node: cst.Import) -> None:
        if any(isinstance(a, cst.ImportAlias) and a.name.value == "pathlib" for a in node.names):
            self.has_pathlib = True
        if any(isinstance(a, cst.ImportAlias) and a.name.value == "json" for a in node.names):
            self.has_json = True

    def visit_Assign(self, node: cst.Assign) -> None:
        self._check_targets(node.targets)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if isinstance(node.target, cst.Name):
            self._check_name(node.target.value)

    def _check_targets(self, targets: Sequence[cst.AssignTarget]) -> None:
        for t in targets:
            if isinstance(t.target, cst.Name):
                self._check_name(t.target.value)

    def _check_name(self, name: str) -> None:
        if name == "INTEGRATION_PATH":
            self.has_int_path = True
        elif name == "CONFIG_PATH":
            self.has_config_path = True
        elif name == "CONFIG":
            self.has_config = True

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        new_body = list(updated_node.body)

        # Add assignments if missing
        if not self.has_int_path:
            new_body.append(
                cst.parse_statement("INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent")
            )
        if not self.has_config_path:
            new_body.append(
                cst.parse_statement("CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / 'config.json'")
            )
        if not self.has_config:
            new_body.append(
                cst.parse_statement("CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}")
            )

        # Add imports if missing
        if not self.has_get_def:
            new_body.insert(0, cst.parse_statement("from integration_testing.common import get_def_file_content"))
        if not self.has_json:
            new_body.insert(0, cst.parse_statement("import json"))
        if not self.has_pathlib:
            new_body.insert(0, cst.parse_statement("import pathlib"))
        if not self.has_future:
            new_body.insert(0, cst.parse_statement("from __future__ import annotations"))

        # Ensure __future__ is always first
        future_idx = -1
        for i, stmt in enumerate(new_body):
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and isinstance(stmt.body[0], cst.ImportFrom)
                and stmt.body[0].module.value == "__future__"
            ):
                future_idx = i
                break

        if future_idx > 0:
            future_stmt = new_body.pop(future_idx)
            new_body.insert(0, future_stmt)

        return updated_node.with_changes(body=tuple(new_body))


# --- Main Engine ---


class IntegrationRefactorer:
    """The core engine for refactoring integrations."""

    def __init__(
        self, integrations_root: Path, dst_path: Path, tests_dir: Path, integrations_list: Optional[str] = None
    ):
        self.integrations_root = integrations_root.resolve()
        self.dst_path = dst_path.resolve()
        self.tests_dir = tests_dir.resolve()
        self.integrations_list = integrations_list
        self.repo = IntegrationsRepo(self.integrations_root, self.dst_path, default_source=False)

    def process_all(self):
        """Processes integrations found in the root directory or from the provided list string."""
        if self.integrations_list:
            target_names = [word for word in self.integrations_list.split() if not word.startswith("(")]
            integrations = []
            for name in target_names:
                p = self.integrations_root / name
                if p.is_dir() and mp.core.file_utils.is_integration(p):
                    integrations.append(p)
                else:
                    logger.warning(f"Integration target not found or invalid: {name}")
        else:
            integrations = [
                p for p in self.integrations_root.iterdir() if p.is_dir() and mp.core.file_utils.is_integration(p)
            ]

        if not integrations:
            logger.warning(f"No integrations found in {self.integrations_root}")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Refactoring integrations...", total=len(integrations))
            for integration_path in integrations:
                try:
                    self.refactor_single(integration_path)
                except Exception as e:
                    logger.error(f"Failed to refactor {integration_path.name}: {e}", exc_info=True)
                progress.advance(task)

    def refactor_single(self, integration_path: Path):
        """Refactors a single integration."""
        integration_name = integration_path.name
        deconstructed_path = self.dst_path / str_to_snake_case(integration_name)

        logger.info(f"[bold blue]Processing: {integration_name}[/bold blue]")

        # 1. Widgets
        self.convert_widgets(integration_path)

        # 2. Deconstruct
        logger.info("Deconstructing integration...")
        self.repo.deconstruct_integration(integration_path)

        # Ensure root __init__.py exists
        (deconstructed_path / "__init__.py").touch(exist_ok=True)
        logger.debug(f"Ensured root __init__.py exists in {deconstructed_path.name}")

        self.copy_ai_descriptions(integration_path, deconstructed_path)

        # 3. Tests
        self.convert_tests(integration_name, deconstructed_path)

        # 4. Version & Sync
        self.increment_version_and_sync(deconstructed_path, integration_name)

        # 5. License Headers
        self.add_license_headers(deconstructed_path)

        # 6. Ruff Exclude
        self.add_to_ruff_specific_integrations(deconstructed_path.name)

    def copy_ai_descriptions(self, integration_path: Path, deconstructed_path: Path):
        src = integration_path / "resources" / "ai" / "actions_ai_description.yaml"
        if src.is_file():
            dst_dir = deconstructed_path / "resources" / "ai"
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_dir / src.name)
        else:
            logger.info(f"No actions_ai_description.yaml found for {integration_path.name}, skipping.")

    def convert_widgets(self, integration_path: Path):
        widgets_dir = integration_path / WIDGETS_DIR
        if not widgets_dir.is_dir():
            logger.debug(f"No 'Widgets' directory in {integration_path.name}")
            return

        for json_file in widgets_dir.glob("*.json"):
            logger.debug(f"Processing widget file: {json_file.name}")
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                converted = self._transform_widget_data(data)
                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(converted, f, indent=4)
            except Exception as e:
                logger.error(f"Error converting widget {json_file.name}: {e}")

    @staticmethod
    def _transform_widget_data(data: Dict[str, Any]) -> Dict[str, Any]:
        transformed = {}
        for key, value in data.items():
            new_key = _capitalize_first_letter(key)
            if new_key == "DataDefinition":
                transformed[new_key] = value
            elif new_key == "ConditionsGroup" and isinstance(value, dict):
                transformed_group = {}
                for cg_key, cg_value in value.items():
                    new_cg_key = _capitalize_first_letter(cg_key)
                    if new_cg_key == "Conditions" and isinstance(cg_value, list):
                        transformed_group[new_cg_key] = [
                            {_capitalize_first_letter(k): v for k, v in item.items()}
                            for item in cg_value
                            if isinstance(item, dict)
                        ]
                    else:
                        transformed_group[new_cg_key] = cg_value
                transformed[new_key] = transformed_group
            else:
                transformed[new_key] = value
        return transformed

    def convert_tests(self, integration_name: str, deconstructed_path: Path):
        tests_src_path = self.tests_dir / "integrations" / integration_name
        tests_dest_path = deconstructed_path / "tests"
        deconstructed_name = deconstructed_path.name

        if tests_src_path.is_dir() and not tests_dest_path.is_dir():
            shutil.copytree(tests_src_path, tests_dest_path)

        self._cleanup_test_files(tests_dest_path)
        use_local_import_test = self._handle_test_dependencies(deconstructed_path, tests_dest_path, integration_name)
        self._refactor_common_py(tests_dest_path, use_local_import_test)

        for file_path in tests_dest_path.rglob("*.py"):
            self._transform_python_file(file_path, integration_name, deconstructed_name)

        for root, _, _ in os.walk(tests_dest_path):
            (Path(root) / "__init__.py").touch(exist_ok=True)

        if not use_local_import_test:
            self._standardize_conftest(tests_dest_path)

    def _cleanup_test_files(self, tests_path: Path):
        paths_to_delete = [tests_path / PYTHONPATH_FILE] + list(tests_path.rglob("test_imports.py"))
        for file in paths_to_delete:
            if file.exists():
                file.unlink()
                logger.debug(f"Cleaned up file: {file}")

    def _handle_test_dependencies(self, deconstructed_path: Path, tests_dest_path: Path, integration_name: str) -> bool:
        pyproject_path = deconstructed_path / PYPROJECT_TOML
        if not pyproject_path.exists():
            return False

        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)

        dev_deps = pyproject_data.get("dependency-groups", {}).get("dev", [])
        reg_deps = pyproject_data.get("project", {}).get("dependencies", [])
        all_deps = dev_deps + reg_deps

        use_local_import_test = False
        if not any(d.startswith("integration-testing") for d in dev_deps):
            if not any(d.startswith("tipcommon") for d in all_deps):
                self._add_local_deps(deconstructed_path)
            else:
                self._check_mock_imports(tests_dest_path, integration_name)
                use_local_import_test = True
        logger.debug(
            f"Dependency analysis complete for {integration_name}. use_local_import_test={use_local_import_test}"
        )
        return use_local_import_test

    @staticmethod
    def _add_local_deps(path: Path):
        local_path = get_local_packages_path()

        def find_latest_whl(package_name: str, subfolder: str) -> Optional[str]:
            folder = local_path / subfolder / "whls"
            if not folder.is_dir():
                return None
            whls = list(folder.glob(f"{package_name}-*.whl"))
            if not whls:
                return None
            # Return the one with highest version (simplistic string sort for now)
            return str(sorted(whls)[-1])

        whls = [
            find_latest_whl("EnvironmentCommon", "envcommon"),
            find_latest_whl("integration_testing", "integration_testing_whls"),
            find_latest_whl("TIPCommon", "tipcommon"),
        ]
        whls = [w for w in whls if w is not None]

        add_dependencies_to_toml(path, ["pytest-mock"], whls)

    @staticmethod
    def _check_mock_imports(path: Path, integration_name: str) -> None:
        for file in path.rglob("*.py"):
            content = file.read_text()
            if "from Tests.mocks" in content or "import Tests.mocks" in content:
                error_msg = (
                    f"CRITICAL: Mock imports found in integration {integration_name}'s tests. "
                    f"Manual intervention required! Aborting refactor for this integration."
                )
                console.print(f"[bold red on white]{error_msg}[/bold red on white]")
                logger.error(error_msg)
                raise RuntimeError(error_msg)

    def _refactor_common_py(self, tests_path: Path, use_local_import_test: bool = False):
        common_py = tests_path / "common.py"
        content = common_py.read_text(encoding="utf-8") if common_py.exists() else ""

        tree = cst.parse_module(content)
        modified = tree.visit(UpsertIntegrationPathTransformer())
        common_py.write_text(modified.code, encoding="utf-8")

        test_defaults = tests_path / "test_defaults"
        test_defaults.mkdir(exist_ok=True)
        if use_local_import_test:
            (test_defaults / "test_imports.py").write_text(LOCAL_IMPORT_TEST_CONTENT)
        else:
            (test_defaults / "test_imports.py").write_text(NEW_IMPORT_TEST_CONTENT)

    def _transform_python_file(self, file_path: Path, integration_name: str, deconstructed_name: str):
        logger.debug(f"Analyzing imports and logic in file: {file_path.name}")
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = cst.parse_module(content)

            # Apply Import remapping
            tree = tree.visit(ImportTransformer(integration_name, deconstructed_name))

            # Apply isinstance transformation
            tree = tree.visit(SDKInstanceTransformer())

            if content != tree.code:
                file_path.write_text(tree.code, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to transform {file_path.name}: {e}")

    @staticmethod
    def _standardize_conftest(tests_path: Path):
        conftest = tests_path / "conftest.py"
        plugin_line = 'pytest_plugins = ("integration_testing.conftest",)'

        session_patch = (
            "\n@pytest.fixture(autouse=True)\n"
            "def script_session(monkeypatch):\n"
            "    from TIPCommon.base.utils import CreateSession\n"
            "    import requests\n"
            "    session = requests.Session()\n"
            "    monkeypatch.setattr(CreateSession, 'create_session', lambda *args, **kwargs: session)\n"
            "    return session\n"
        )

        if not conftest.exists():
            conftest.write_text(f"import pytest\nimport requests\n{plugin_line}\n{session_patch}", encoding="utf-8")
            return

        content = conftest.read_text(encoding="utf-8")

        # Add plugin line if missing
        if plugin_line not in content:
            content = f"{plugin_line}\n{content}"

        # Add session patch if missing
        if "monkeypatch.setattr(CreateSession" not in content:
            content += session_patch

        conftest.write_text(content, encoding="utf-8")

    def increment_version_and_sync(self, path: Path, name: str):
        pyproject_path = path / PYPROJECT_TOML
        if not pyproject_path.is_file():
            return

        with open(pyproject_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        v = data["project"]["version"].split(".")
        v[0] = str(int(v[0]) + 1)
        if len(v) > 1:
            v[1] = "0"
        new_v = ".".join(v)
        logger.debug(f"Bumping version from {data['project']['version']} to {new_v}")
        data["project"]["version"] = new_v

        with open(pyproject_path, "w", encoding="utf-8") as f:
            toml.dump(data, f)

        # Release Notes
        rn_path = path / RELEASE_NOTES_FILE
        note = MIGRATION_RELEASE_NOTE_TEMPLATE.copy()
        note.update({
            "integration_version": float(new_v),
            "item_name": name,
            "publish_time": datetime.now().strftime("%Y-%m-%d"),
        })
        with open(rn_path, "a", encoding="utf-8") as f:
            f.write("\n")
            yaml.dump([note], f, default_flow_style=False, sort_keys=False)

        logger.info(f"Running 'uv sync' in {path}...")
        subprocess.run(["uv", "sync"], cwd=path, check=True)

    @staticmethod
    def add_license_headers(path: Path):
        try:
            subprocess.run(["addlicense", "."], cwd=path, check=True)
        except Exception as e:
            logger.error(f"Failed to add license headers: {e}")

    def add_to_ruff_specific_integrations(self, name: str):
        ruff_path = self.dst_path / "ruff.toml"
        if not ruff_path.is_file():
            # Fallback if dst_path doesn't have it
            ruff_path = get_marketplace_path() / "content" / "response_integrations" / "google" / "ruff.toml"
            if not ruff_path.is_file():
                return

        lines = ruff_path.read_text(encoding="utf-8").splitlines()
        entry = f'"{name}/**" = ["ALL"]'
        if any(line.strip() == entry for line in lines):
            logger.debug(f"Ruff entry for {name} already exists.")
            return

        new_lines = []
        in_specific_block = False
        inserted = False

        for line in lines:
            stripped = line.strip()
            if stripped == "# Specific Integrations":
                in_specific_block = True
                new_lines.append(line)
                continue

            if in_specific_block and not inserted:
                if not stripped or stripped.startswith("["):
                    new_lines.append(entry)
                    inserted = True
                    in_specific_block = False

            new_lines.append(line)

        if in_specific_block and not inserted:
            new_lines.append(entry)

        ruff_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.debug(f"Added ruff entry for {name}")


def main():
    parser = argparse.ArgumentParser(description="Refactor a directory of integrations.")
    parser.add_argument("integrations_path", type=str, help="Source integrations directory.")
    parser.add_argument("dst_path", type=str, help="Destination directory.")
    parser.add_argument("--tests-dir", type=str, required=True, help="Path to 'Tests' directory.")
    parser.add_argument(
        "--integrations-list", type=str, help="Optional space-separated list of integrations to process."
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    refactorer = IntegrationRefactorer(
        Path(args.integrations_path),
        Path(args.dst_path),
        Path(args.tests_dir),
        integrations_list=args.integrations_list,
    )
    refactorer.process_all()


if __name__ == "__main__":
    main()
