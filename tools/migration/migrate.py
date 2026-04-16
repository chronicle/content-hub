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


'''
Reply from team eng:


fix 1 - a good fix, i applied it and it worked
fix 2 - good point but not the right fix - i applied a logic that in a case where tipcommon is in an too old version to use integration-testing package, the script will copy the import-test logic and use it instead of using the package. (if there are more tests than that for this integrations, an error is raised for it because manual attention is needed)
fix 3- good fix
fix 4- not true. ImportTransformer's job is only relevant for transforming from using local Tests/mocks dir, to use integration-testing package. so this is only needed on test files, which is what is done right now.
fix 5- could be right, its a small edge case so didnt check that yet.


טוב אחרי התיקונים הטובים שלו מפה (העתקתי לך את הסקריפט עם התיקונים לאותו מקום) בעצם עדיין נשאר העניין המרכזי שאמרתי לך, וזה שזה עושה real api calls במקום להשתמש בהצלחה במוקים מהפקג׳ של טל (integration-testing)
אז תכלס אשמח שנמשיך לשבת על זה 




'''









from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field
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

# integration_testing 2.x renamed get_json_file_content -> get_def_file_content.
# Legacy tests use the old name. The mapping renames both calls and imports.
TESTS_FUNCTIONS_MAPPING = {"get_json_file_content": "get_def_file_content"}

TIPCOMMON_FUNCTIONS_MAPPING = {
    # --- TIPCommon.extraction ---
    "extract_configuration_param": "TIPCommon.extraction",
    "extract_action_param": "TIPCommon.extraction",
    "extract_connector_param": "TIPCommon.extraction",
    "extract_job_param": "TIPCommon.extraction",
    "extract_script_param": "TIPCommon.extraction",
    # --- TIPCommon.transformation ---
    "construct_csv": "TIPCommon.transformation",
    "add_prefix_to_dict": "TIPCommon.transformation",
    "dict_to_flat": "TIPCommon.transformation",
    "flat_dict_to_csv": "TIPCommon.transformation",
    "convert_comma_separated_to_list": "TIPCommon.transformation",
    "convert_list_to_comma_string": "TIPCommon.transformation",
    "string_to_multi_value": "TIPCommon.transformation",
    "add_prefix_to_dict_keys": "TIPCommon.transformation",
    "adjust_to_csv": "TIPCommon.transformation",
    "get_unicode": "TIPCommon.transformation",
    # --- TIPCommon.smp_time ---
    "is_approaching_timeout": "TIPCommon.smp_time",
    "get_last_success_time": "TIPCommon.smp_time",
    "save_timestamp": "TIPCommon.smp_time",
    "validate_timestamp": "TIPCommon.smp_time",
    "unix_now": "TIPCommon.smp_time",
    "siemplify_save_timestamp": "TIPCommon.smp_time",
    "siemplify_fetch_timestamp": "TIPCommon.smp_time",
    "convert_datetime_to_unix_time": "TIPCommon.smp_time",
    "utc_now": "TIPCommon.smp_time",
    # --- TIPCommon.filters ---
    "filter_old_alerts": "TIPCommon.filters",
    "pass_whitelist_filter": "TIPCommon.filters",
    "filter_old_ids": "TIPCommon.filters",
    # --- TIPCommon.utils ---
    "is_overflowed": "TIPCommon.utils",
    "is_test_run": "TIPCommon.utils",
    "none_to_default_value": "TIPCommon.utils",
    "platform_supports_db": "TIPCommon.utils",
    "is_empty_string_or_none": "TIPCommon.utils",
    # --- TIPCommon.smp_io ---
    "read_ids": "TIPCommon.smp_io",
    "write_ids": "TIPCommon.smp_io",
    "read_content": "TIPCommon.smp_io",
    "write_content": "TIPCommon.smp_io",
    "write_ids_with_timestamp": "TIPCommon.smp_io",
    "read_ids_by_timestamp": "TIPCommon.smp_io",
    # --- TIPCommon.consts ---
    "UNIX_FORMAT": "TIPCommon.consts",
    "WHITELIST_FILTER": "TIPCommon.consts",
    "BLACKLIST_FILTER": "TIPCommon.consts",
    "NUM_OF_MILLI_IN_SEC": "TIPCommon.consts",
    "TIMEOUT_THRESHOLD": "TIPCommon.consts",
    "DATETIME_FORMAT": "TIPCommon.consts",
    "IDS_DB_KEY": "TIPCommon.consts",
    "IDS_FILE_NAME": "TIPCommon.consts",
}

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


class ImportTransformer(cst.CSTTransformer):
    """Handles remapping of imports during integration refactoring."""

    def __init__(self, integration_name: str, deconstructed_name: str,
                 core_module_names: set[str] | None = None):
        super().__init__()
        self.integration_name = integration_name
        self.deconstructed_name = deconstructed_name
        self.needs_abc_import = False
        self.has_abc_import = False
        # Names of .py files in core/ (without extension) for bare import detection
        self.core_module_names = core_module_names or set()

    def _remap_integration_path(self, path: str) -> str:
        prefix = f"Integrations.{self.integration_name}"
        if not path.startswith(prefix):
            return path

        parts = path[len(prefix) :].strip(".").split(".")
        if parts and parts[0] in INTEGRATIONS_PATH_MAPPING:
            parts[0] = INTEGRATIONS_PATH_MAPPING[parts[0]]

        return ".".join(filter(None, [self.deconstructed_name] + parts))

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
            return cst.RemoveFromParent()

        # Handle SDK module relocations (CaseInfo moved from SiemplifyConnectors
        # to SiemplifyConnectorsDataModel)
        if module_path == "SiemplifyConnectors" and isinstance(updated_node.names, (list, tuple)):
            names = [a.name.value for a in updated_node.names if isinstance(a, cst.ImportAlias)]
            if "CaseInfo" in names:
                return updated_node.with_changes(
                    module=cst.parse_expression("soar_sdk.SiemplifyConnectorsDataModel"),
                    relative=(),
                )

        remapped_path = _remap_sdk_path(module_path)

        if module_path.startswith(f"Integrations.{self.integration_name}"):
            remapped = self._remap_integration_path(remapped_path)
            return updated_node.with_changes(
                module=cst.parse_expression(remapped),
                relative=(),
            )

        test_prefix = f"Tests.integrations.{self.integration_name}"
        if module_path.startswith(test_prefix):
            new_module = module_path.replace(test_prefix, f"{self.deconstructed_name}.tests", 1)
            return updated_node.with_changes(
                module=cst.parse_expression(new_module),
                relative=(),
            )

        if "Tests.mocks" in module_path:
            return self._handle_mock_utility_imports(updated_node, module_path)

        if module_path == "TIPCommon":
            return self._handle_tip_common_imports(updated_node)

        if remapped_path != module_path:
            return updated_node.with_changes(
                module=cst.parse_expression(remapped_path), relative=()
            )

        # Detect bare imports matching core/ module files
        # e.g., "from datamodels import X" -> "from .datamodels import X" (in core/)
        #    or "from datamodels import X" -> "from ..core.datamodels import X" (in actions/)
        if self.core_module_names and module_path in self.core_module_names:
            return updated_node.with_changes(
                module=cst.parse_expression(f"core.{module_path}"),
                relative=(cst.Dot(), cst.Dot()),
            )

        return updated_node

    def _handle_tip_common_imports(self, node: cst.ImportFrom) -> Union[cst.ImportFrom, cst.FlattenSentinel]:
        if isinstance(node.names, cst.ImportStar):
            return node

        submodule_to_names: Dict[str, list[cst.ImportAlias]] = {}
        for alias in node.names:
            if not isinstance(alias, cst.ImportAlias):
                continue
            name = alias.name.value
            submodule = TIPCOMMON_FUNCTIONS_MAPPING.get(name, "TIPCommon")
            submodule_to_names.setdefault(submodule, []).append(alias)

        if not submodule_to_names:
            return node

        if len(submodule_to_names) == 1:
            submodule = next(iter(submodule_to_names))
            return node.with_changes(module=cst.parse_expression(submodule), relative=())

        new_imports = []
        for submodule, names in submodule_to_names.items():
            # Strip trailing comma from last alias to avoid syntax errors
            last = names[-1]
            if isinstance(getattr(last, "comma", None), cst.Comma):
                names[-1] = last.with_changes(comma=cst.MaybeSentinel.DEFAULT)
            new_imports.append(
                node.with_changes(
                    module=cst.parse_expression(submodule), names=tuple(names), relative=()
                )
            )

        return cst.FlattenSentinel(new_imports)

    def _handle_mock_utility_imports(self, node: cst.ImportFrom, path: str) -> cst.ImportFrom:
        new_path = path.replace("Tests.mocks", "integration_testing")
        for old, new in TESTS_PATH_MAPPING.items():
            new_path = new_path.replace(old, new)

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
        return node.with_changes(
            module=cst.parse_expression(new_path), relative=(), names=tuple(new_names)
        )

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

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Rename function definitions listed in TESTS_FUNCTIONS_MAPPING."""
        name = updated_node.name.value
        if name in TESTS_FUNCTIONS_MAPPING:
            new_name = TESTS_FUNCTIONS_MAPPING[name]
            return updated_node.with_changes(name=cst.Name(new_name))
        return updated_node

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        raw_val = updated_node.value.strip("'\"")
        quote = updated_node.value[0]

        if raw_val.startswith(f"Integrations.{self.integration_name}"):
            remapped = self._remap_integration_path(raw_val)
            return updated_node.with_changes(value=f"{quote}{remapped}{quote}")

        test_prefix = f"Tests.integrations.{self.integration_name}"
        if raw_val.startswith(test_prefix):
            replaced = raw_val.replace(test_prefix, "tests", 1)
            return updated_node.with_changes(value=f"{quote}{replaced}{quote}")

        if raw_val.endswith((".actiondef", ".connectordef", ".jobdef")):
            new_val = (
                raw_val
                .replace(".actiondef", ".yaml")
                .replace(".connectordef", ".yaml")
                .replace(".jobdef", ".yaml")
            )
            return updated_node.with_changes(value=f"{quote}{new_val}{quote}")
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
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
            idx = 1 if new_body and self._is_future(new_body[0]) else 0
            new_body.insert(idx, cast(cst.SimpleStatementLine, cst.parse_statement("import abc")))
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
    """Ensures necessary imports and INTEGRATION_PATH exist in common.py."""

    def __init__(self):
        super().__init__()
        self.has_future = False
        self.has_pathlib = False
        self.has_int_path = False

    def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
        if node.module and isinstance(node.module, cst.Name) and node.module.value == "__future__":
            if isinstance(node.names, Sequence):
                if any(
                    isinstance(a, cst.ImportAlias) and a.name.value == "annotations"
                    for a in node.names
                ):
                    self.has_future = True

    def visit_Import(self, node: cst.Import) -> None:
        if any(isinstance(a, cst.ImportAlias) and a.name.value == "pathlib" for a in node.names):
            self.has_pathlib = True

    def leave_Assign(
        self, original_node: cst.Assign, updated_node: cst.Assign
    ) -> Union[cst.Assign, cst.AnnAssign]:
        if len(updated_node.targets) == 1:
            target = updated_node.targets[0].target
            if isinstance(target, cst.Name) and target.value == "INTEGRATION_PATH":
                self.has_int_path = True
                return cst.AnnAssign(
                    target=target,
                    annotation=cst.Annotation(cst.parse_expression("pathlib.Path")),
                    value=cst.parse_expression("pathlib.Path(__file__).parent.parent"),
                )
        return updated_node

    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> cst.AnnAssign:
        if (
            isinstance(updated_node.target, cst.Name)
            and updated_node.target.value == "INTEGRATION_PATH"
        ):
            self.has_int_path = True
            return updated_node.with_changes(
                annotation=cst.Annotation(cst.parse_expression("pathlib.Path")),
                value=cst.parse_expression("pathlib.Path(__file__).parent.parent"),
            )
        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        new_body = list(updated_node.body)
        if not self.has_int_path:
            new_body.append(
                cast(
                    cst.SimpleStatementLine,
                    cst.parse_statement(
                        "INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent"
                    ),
                )
            )
        if not self.has_pathlib:
            new_body.insert(0, cast(cst.SimpleStatementLine, cst.parse_statement("import pathlib")))
        if not self.has_future:
            new_body.insert(
                0,
                cast(
                    cst.SimpleStatementLine,
                    cst.parse_statement("from __future__ import annotations"),
                ),
            )
        return updated_node.with_changes(body=tuple(new_body))


# --- Main Engine ---


class IntegrationRefactorer:
    """The core engine for refactoring integrations."""

    def __init__(self, integrations_root: Path, dst_path: Path, tests_dir: Path, integrations_list: Optional[str] = None, skip_verify_ssl: bool = False):
        self.integrations_root = integrations_root.resolve()
        self.dst_path = dst_path.resolve()
        self.tests_dir = tests_dir.resolve()
        self.integrations_list = integrations_list
        self.skip_verify_ssl = skip_verify_ssl
        self.repo = IntegrationsRepo(self.integrations_root, self.dst_path, default_source=False)

    def process_all(self):
        """Processes integrations found in the root directory or from the provided list string."""
        if self.integrations_list:
            target_names = [
                word for word in self.integrations_list.split() 
                if not word.startswith("(")
            ]
            integrations = []
            for name in target_names:
                p = self.integrations_root / name
                if p.is_dir() and mp.core.file_utils.is_integration(p):
                    integrations.append(p)
                else:
                    logger.warning(f"Integration target not found or invalid: {name}")
        else:
            integrations = [
                p
                for p in self.integrations_root.iterdir()
                if p.is_dir() and mp.core.file_utils.is_integration(p)
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

        self.copy_ai_descriptions(integration_path, deconstructed_path)

        # 2a. Fix requires-python, release notes, and Verify SSL
        self._fix_requires_python(deconstructed_path)
        self._fix_release_notes(deconstructed_path)
        if not self.skip_verify_ssl:
            self._fix_verify_ssl(deconstructed_path)

        # 2b. Fix imports in integration source files (actions, core, etc.)
        logger.info("Fixing imports in integration source files...")
        # Collect core/ module names for bare import detection
        core_dir = deconstructed_path / "core"
        core_module_names = {
            f.stem for f in core_dir.glob("*.py")
            if f.stem != "__init__"
        } if core_dir.is_dir() else set()

        excluded = {".venv", "tests", "__pycache__"}
        for file_path in deconstructed_path.rglob("*.py"):
            if not any(p in excluded for p in file_path.parts):
                self._transform_python_file(file_path, integration_name, deconstructed_path.name, core_module_names)

        # 2c. Replace SiemplifySession with requests.Session
        # SiemplifySession was a TIPCommon 1.x class (requests.Session subclass
        # that masked sensitive data in error messages). Removed in TIPCommon 2.x.
        # Only 5 integrations use it. Direct rewrite is cleanest.
        self._replace_siemplify_session(deconstructed_path)

        # 2d. Rename _init_managers -> _init_api_clients (TIPCommon 2.x rename)
        self._rename_deprecated_methods(deconstructed_path)

        # 3. Tests
        self.convert_tests(integration_name, deconstructed_path)

        # 4. Version & Sync
        self.increment_version_and_sync(deconstructed_path, integration_name)

        # 5. License Headers
        self.add_license_headers(deconstructed_path)

        # 6. Ruff Exclude (skip in batch mode to avoid race condition on shared file)
        if not os.environ.get("MIGRATION_BATCH_MODE"):
            self.add_to_ruff_specific_integrations(deconstructed_path.name)

    @staticmethod
    def _fix_release_notes(deconstructed_path: Path):
        """Fix empty publish_time in release notes (validation requires YYYY-MM-DD)."""
        rn_path = deconstructed_path / RELEASE_NOTES_FILE
        if not rn_path.exists():
            return
        content = rn_path.read_text(encoding="utf-8")
        notes = yaml.safe_load(content)
        if not notes:
            return
        changed = False
        for note in notes:
            pt = note.get("publish_time")
            if not pt or pt == "":
                note["publish_time"] = "2020-01-01"
                changed = True
        if changed:
            with open(rn_path, "w", encoding="utf-8") as f:
                yaml.dump(notes, f, default_flow_style=False, sort_keys=False)
            logger.info("Fixed empty publish_time entries in release_notes.yaml")

    @staticmethod
    def _fix_verify_ssl(deconstructed_path: Path):
        """Ensure Verify SSL parameter exists with default 'true' and correct description."""
        def_path = deconstructed_path / "definition.yaml"
        if not def_path.exists():
            return
        data = yaml.safe_load(def_path.read_text(encoding="utf-8"))
        if not data:
            return
        
        params = data.setdefault("parameters", [])
        ssl_param = next((p for p in params if p.get("name") == "Verify SSL"), None)
        
        if not ssl_param:
            ssl_param = {
                "name": "Verify SSL",
                "type": "boolean",
                "is_mandatory": false,
                "integration_identifier": data.get("identifier", deconstructed_path.name)
            }
            params.append(ssl_param)
            changed = True
        else:
            changed = False

        if not ssl_param.get("default_value") or ssl_param["default_value"] == "":
            ssl_param["default_value"] = "true"
            changed = True
            
        expected_desc = (
            "If selected, the integration validates the SSL certificate "
            f"when connecting to {data.get('name', 'the server')}. Selected by default."
        )
        if ssl_param.get("description") != expected_desc:
            ssl_param["description"] = expected_desc
            changed = True

        if changed:
            with open(def_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            logger.info("Fixed/Added Verify SSL in definition.yaml")

    @staticmethod
    def _fix_requires_python(deconstructed_path: Path):
        """Fix requires-python to include upper bound (>=3.11,<3.12)."""
        pyproject_path = deconstructed_path / PYPROJECT_TOML
        if not pyproject_path.exists():
            return
        content = pyproject_path.read_text(encoding="utf-8")
        if 'requires-python = ">=3.11"' in content:
            content = content.replace(
                'requires-python = ">=3.11"',
                'requires-python = ">=3.11,<3.12"'
            )
            pyproject_path.write_text(content, encoding="utf-8")

    def copy_ai_descriptions(self, integration_path: Path, deconstructed_path: Path):
        src = integration_path / "resources" / "ai" / "actions_ai_description.yaml"
        if src.is_file():
            dst_dir = deconstructed_path / "resources"
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
        self._handle_test_dependencies(deconstructed_path, tests_dest_path)
        self._refactor_common_py(tests_dest_path)

        for file_path in tests_dest_path.rglob("*.py"):
            self._transform_python_file(file_path, integration_name, deconstructed_name)

        for root, _, _ in os.walk(tests_dest_path):
            (Path(root) / "__init__.py").touch(exist_ok=True)

        self._ensure_conftest_plugins(tests_dest_path)

    def _cleanup_test_files(self, tests_path: Path):
        paths_to_delete = [tests_path / PYTHONPATH_FILE] + list(tests_path.rglob("test_imports.py"))
        for file in paths_to_delete:
            if file.exists():
                file.unlink()

    def _handle_test_dependencies(self, deconstructed_path: Path, tests_dest_path: Path):
        pyproject_path = deconstructed_path / PYPROJECT_TOML
        if not pyproject_path.exists():
            return

        with pyproject_path.open("rb") as f:
            pyproject_data = tomllib.load(f)

        dev_deps = pyproject_data.get("dependency-groups", {}).get("dev", [])
        reg_deps = pyproject_data.get("project", {}).get("dependencies", [])
        all_deps = dev_deps + reg_deps

        if not any(d.startswith("integration-testing") for d in dev_deps):
            self._add_local_deps(deconstructed_path)
            self._check_mock_imports(tests_dest_path)

    @staticmethod
    def _find_packages_dir(path: Path) -> Path | None:
        """Walk up from integration path to find the packages/ directory."""
        candidate = path.resolve()
        while candidate.parent != candidate:
            if (candidate / "packages" / "tipcommon").exists():
                return candidate / "packages"
            candidate = candidate.parent
        return None

    @staticmethod
    def _add_local_deps(path: Path):
        # Discover packages/ by walking up from integration path.
        # Don't use get_local_packages_path() — mp config gets reverted.
        local_path = IntegrationRefactorer._find_packages_dir(path)
        if local_path is None:
            logger.warning("Cannot find packages/ directory — dev deps will be missing")
            return

        whls = {
            "environmentcommon": local_path / "envcommon" / "whls" / "EnvironmentCommon-1.0.3-py3-none-any.whl",
            "integration-testing": local_path / "integration_testing_whls" / "integration_testing-2.2.22-py3-none-any.whl",
            "tipcommon": local_path / "tipcommon" / "whls" / "TIPCommon-2.2.22-py2.py3-none-any.whl",
        }
        existing = {name: p for name, p in whls.items() if p.exists()}
        if not existing:
            logger.warning(f"No wheel files found at {local_path}")
            return

        # Write deps directly to pyproject.toml instead of calling uv add
        # (uv add fails when --default-index is missing from the installed mp)
        pyproject_path = path / PYPROJECT_TOML
        with open(pyproject_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        dev_group = data.setdefault("dependency-groups", {}).setdefault("dev", [])
        sources = data.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})

        # Add wheel-based deps
        for name, whl_path in existing.items():
            if not any(name in d for d in dev_group):
                dev_group.append(name)
            rel_path = os.path.relpath(whl_path, path)
            sources[name] = {"path": rel_path}

        # Ensure base dev deps are present (pytest, soar-sdk, etc.)
        # These may have been lost if the deconstruct step's uv add failed
        base_dev_deps = {
            "pytest>=8.3.5": None,
            "pytest-json-report>=1.5.0": None,
            "pytest-mock>=3.14.0": None,
            "soar-sdk": {"git": "https://github.com/chronicle/soar-sdk.git"},
        }
        for dep, source in base_dev_deps.items():
            dep_name = dep.split(">=")[0].split("==")[0]
            if not any(dep_name in d for d in dev_group):
                dev_group.append(dep)
            if source and dep_name not in sources:
                sources[dep_name] = source

        # Ensure PyPI index is configured
        uv_section = data.setdefault("tool", {}).setdefault("uv", {})
        if "index" not in uv_section:
            uv_section["index"] = [{"url": "https://pypi.org/simple", "default": True}]

        with open(pyproject_path, "w", encoding="utf-8") as f:
            toml.dump(data, f)
        # uv sync will be called by increment_version_and_sync() later

    @staticmethod
    def _add_test_framework_deps(path: Path):
        local_path = IntegrationRefactorer._find_packages_dir(path)
        if local_path is None:
            return

        whls = {
            "environmentcommon": local_path / "envcommon" / "whls" / "EnvironmentCommon-1.0.3-py3-none-any.whl",
            "integration-testing": local_path / "integration_testing_whls" / "integration_testing-2.2.22-py3-none-any.whl",
        }
        existing = {name: p for name, p in whls.items() if p.exists()}
        if not existing:
            return

        pyproject_path = path / PYPROJECT_TOML
        with open(pyproject_path, "r", encoding="utf-8") as f:
            data = toml.load(f)

        dev_group = data.setdefault("dependency-groups", {}).setdefault("dev", [])
        sources = data.setdefault("tool", {}).setdefault("uv", {}).setdefault("sources", {})

        for name, whl_path in existing.items():
            if not any(name in d for d in dev_group):
                dev_group.append(name)
            rel_path = os.path.relpath(whl_path, path)
            sources[name] = {"path": rel_path}

        with open(pyproject_path, "w", encoding="utf-8") as f:
            toml.dump(data, f)

    @staticmethod
    def _check_mock_imports(path: Path):
        for file in path.rglob("*.py"):
            content = file.read_text()
            if "from Tests.mocks" in content or "import Tests.mocks" in content:
                logger.warning(f"Manual intervention needed: Mock imports found in {file}")

    def _refactor_common_py(self, tests_path: Path):
        common_py = tests_path / "common.py"
        content = common_py.read_text(encoding="utf-8") if common_py.exists() else ""

        tree = cst.parse_module(content)
        modified = tree.visit(UpsertIntegrationPathTransformer())
        common_py.write_text(modified.code, encoding="utf-8")

        test_defaults = tests_path / "test_defaults"
        test_defaults.mkdir(exist_ok=True)
        (test_defaults / "test_imports.py").write_text(NEW_IMPORT_TEST_CONTENT)

    def _transform_python_file(
        self, file_path: Path, integration_name: str, deconstructed_name: str,
        core_module_names: set[str] | None = None
    ):
        try:
            content = file_path.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(content))
            transformer = ImportTransformer(integration_name, deconstructed_name, core_module_names)
            modified_tree = wrapper.visit(transformer)

            if not wrapper.module.deep_equals(modified_tree):
                file_path.write_text(modified_tree.code, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to transform {file_path.name}: {e}")

    @staticmethod
    def _replace_siemplify_session(deconstructed_path: Path):
        """Replace SiemplifySession (TIPCommon 1.x) with requests.Session.

        SiemplifySession was a requests.Session subclass that masked sensitive
        data in error messages. It was removed in TIPCommon 2.x with no
        replacement. Only 5 legacy integrations use it.

        Rewrites:
          from TIPCommon import SiemplifySession
            -> (removed, requests is already imported)
          self.session = SiemplifySession(sensitive_data_arr=[...])
            -> self.session = requests.Session()
          session = SiemplifySession(...)
            -> session = requests.Session()
          SiemplifySession().encode_data(x)
            -> x[:1] + "..." + x[-1:]  (inline the trivial masking logic)
        """
        import re

        excluded = {".venv", "tests", "__pycache__"}
        for file_path in deconstructed_path.rglob("*.py"):
            if any(p in excluded for p in file_path.parts):
                continue

            content = file_path.read_text(encoding="utf-8")
            if "SiemplifySession" not in content:
                continue

            original = content

            # Step 1: Replace constructor calls FIRST (before removing the name)
            #   SiemplifySession(sensitive_data_arr=[...])  -> requests.Session()
            #   SiemplifySession(...)                       -> requests.Session()
            #   SiemplifySession()                          -> requests.Session()
            # Use a greedy match that handles nested brackets like [api_key]
            content = re.sub(
                r"SiemplifySession\(.*?\)(?=\s*$|\s*\n)",
                "requests.Session()",
                content,
                flags=re.MULTILINE,
            )

            # Step 2: Remove import lines
            # Case 1: sole import — from TIPCommon import SiemplifySession
            content = re.sub(
                r"^from TIPCommon import SiemplifySession\s*\n",
                "",
                content,
                flags=re.MULTILINE,
            )
            # Case 2: part of multi-import — from TIPCommon import X, SiemplifySession, Y
            content = re.sub(
                r",\s*SiemplifySession",
                "",
                content,
            )
            content = re.sub(
                r"SiemplifySession\s*,\s*",
                "",
                content,
            )

            # Step 3: Clean up encode_sensitive_data calls left from SiemplifySession
            # SiemplifySession had encode_sensitive_data() for masking secrets in errors.
            # After rewriting to requests.Session(), these calls will crash (AttributeError).
            content = re.sub(
                r"self\.session\.encode_sensitive_data\(([^)]+)\)",
                r"\1",
                content,
            )

            # Step 4: Ensure 'import requests' is present
            if "import requests" not in content and "requests.Session()" in content:
                lines = content.split("\n")
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith(("import ", "from ")):
                        last_import_idx = i
                lines.insert(last_import_idx + 1, "import requests")
                content = "\n".join(lines)

            if content != original:
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"Replaced SiemplifySession in {file_path.name}")

    @staticmethod
    def _rename_deprecated_methods(deconstructed_path: Path):
        """Rename TIPCommon 1.x abstract methods to 2.x names.

        TIPCommon 2.x renamed _init_managers -> _init_api_clients in the
        Action base class. Legacy integrations that implement the old name
        can't be instantiated (abstract method not implemented).
        """
        excluded = {".venv", "tests", "__pycache__"}
        for file_path in deconstructed_path.rglob("*.py"):
            if any(p in excluded for p in file_path.parts):
                continue
            content = file_path.read_text(encoding="utf-8")
            if "_init_managers" in content:
                content = content.replace("_init_managers", "_init_api_clients")
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"Renamed _init_managers -> _init_api_clients in {file_path.name}")

    @staticmethod
    def _ensure_conftest_plugins(tests_path: Path):
        conftest = tests_path / "conftest.py"
        plugin_line = 'pytest_plugins = ("integration_testing.conftest",)'

        if not conftest.exists():
            conftest.write_text(f"{plugin_line}\n", encoding="utf-8")
            return

        content = conftest.read_text(encoding="utf-8")
        if plugin_line in content:
            return

        parser_config = cst.PartialParserConfig(python_version=cst.KNOWN_PYTHON_VERSION_STRINGS[-1])
        tree = cst.parse_module(content, config=parser_config)
        new_body = list(tree.body)
        idx = next(
            (
                i + 1
                for i, s in reversed(list(enumerate(new_body)))
                if isinstance(s, cst.SimpleStatementLine)
                and isinstance(s.body[0], (cst.Import, cst.ImportFrom))
            ),
            0,
        )

        plugin_stmt = cast(cst.SimpleStatementLine, cst.parse_statement(plugin_line))
        new_body.insert(idx, plugin_stmt)
        conftest.write_text(tree.with_changes(body=tuple(new_body)).code, encoding="utf-8")

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


def main():
    parser = argparse.ArgumentParser(
        description="Refactor a directory of integrations with elegance."
    )
    parser.add_argument("integrations_path", type=str, help="Source integrations directory.")
    parser.add_argument("dst_path", type=str, help="Destination directory.")
    parser.add_argument("--tests-dir", type=str, required=True, help="Path to 'Tests' directory.")
    parser.add_argument("--integrations-list", type=str, help="Optional space-separated list of integrations to process.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--skip-verify-ssl", action="store_true", help="Skip adding/fixing the Verify SSL parameter in definition.yaml.")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    refactorer = IntegrationRefactorer(
        Path(args.integrations_path), Path(args.dst_path), Path(args.tests_dir),
        integrations_list=args.integrations_list,
        skip_verify_ssl=args.skip_verify_ssl,
    )
    refactorer.process_all()


if __name__ == "__main__":
    main()
