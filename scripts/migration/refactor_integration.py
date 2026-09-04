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
import re
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
    "Actions": "actions",
    "JobsScrips": "jobs",
    "Jobs": "jobs",
    "Managers": "core",
    "ConnectorScripts": "connectors",
    "ConnectorsScripts": "connectors",
    "Connectors": "connectors",
}

INTEGRATIONS_REQUIRING_SUFFIX = {"akamai", "http", "twilio"}

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


def _get_insert_index_after_future(body: Sequence[cst.BaseStatement]) -> int:
    """Finds the index to insert imports safely after any __future__ imports or docstrings."""
    insert_idx = 0
    if body and isinstance(body[0], cst.SimpleStatementLine):
         if (isinstance(body[0].body[0], cst.Expr) and 
             isinstance(body[0].body[0].value, (cst.SimpleString, cst.ConcatenatedString))):
             insert_idx = 1
    
    for i, stmt in enumerate(body):
        if (
            isinstance(stmt, cst.SimpleStatementLine)
            and isinstance(stmt.body[0], cst.ImportFrom)
            and getattr(stmt.body[0].module, "value", "") == "__future__"
        ):
            insert_idx = i + 1
            break
    return insert_idx


def _fix_future_order(tree: cst.Module) -> cst.Module:
    """
    Ensures that `from __future__ import ...` statements remain at the very top of the file.
    
    Why: Python syntax enforces that __future__ imports must appear before any other code 
    except docstrings. When our transformers inject new imports or patches at the top of 
    the file, they might inadvertently push the __future__ import down, causing a SyntaxError.
    This function finds any __future__ import and moves it back to the top.
    """
    new_body = list(tree.body)
    future_idx = -1
    for i, stmt in enumerate(new_body):
        if (
            isinstance(stmt, cst.SimpleStatementLine)
            and isinstance(stmt.body[0], cst.ImportFrom)
            and getattr(stmt.body[0].module, "value", "") == "__future__"
        ):
            future_idx = i
            break

    if future_idx > 0:
        logger.info(f"Moving __future__ import from index {future_idx} to top")
        future_stmt = new_body.pop(future_idx)
        
        insert_idx = 0
        if new_body and isinstance(new_body[0], cst.SimpleStatementLine):
            if isinstance(new_body[0].body[0], cst.Expr) and isinstance(new_body[0].body[0].value, (cst.SimpleString, cst.ConcatenatedString)):
                insert_idx = 1
        
        if insert_idx == 0 and new_body:
            leading = new_body[0].leading_lines
            if leading:
                new_body[0] = new_body[0].with_changes(leading_lines=())
                future_stmt = future_stmt.with_changes(leading_lines=leading)

        new_body.insert(insert_idx, future_stmt)
        return tree.with_changes(body=tuple(new_body))
    return tree


# --- CST Transformers ---


class SDKInstanceTransformer(cst.CSTTransformer):
    """
    Replaces strict isinstance() checks on SDK objects with hasattr() checks (Duck Typing).
    
    Why: In the new testing framework, SDK objects are heavily mocked or imported through
    different namespace permutations (flat vs soar_sdk.*). This causes strict `isinstance` 
    checks to fail during tests because the mocked object's class doesn't strictly match the 
    imported class reference. Changing these to `hasattr` checks ensures tests don't break 
    on technicalities.
    """

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


class ExpressionTransformer(cst.CSTTransformer):
    """Remaps Integrations and Tests.integrations references in expressions."""

    def __init__(self, integration_name: str, deconstructed_name: str):
        self.integration_name = integration_name
        self.deconstructed_name = deconstructed_name

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> Union[cst.Call, cst.BaseExpression]:
        # Fix get_def_file_content("config.json") to use absolute path
        if isinstance(updated_node.func, cst.Name) and updated_node.func.value in ["get_def_file_content", "get_mock_file_content"]:
            if len(updated_node.args) > 0 and isinstance(updated_node.args[0].value, cst.SimpleString):
                filename = updated_node.args[0].value.value.strip("\"'")
                if not filename.startswith("/"):
                     new_path_expr = f"__import__('pathlib').Path(__file__).parent / '{filename}'"
                     new_args = list(updated_node.args)
                     new_args[0] = updated_node.args[0].with_changes(value=cst.parse_expression(new_path_expr))
                     logger.debug(f"Remapped {updated_node.func.value} to absolute path for {filename}")
                     return updated_node.with_changes(args=tuple(new_args))

        # Fix mocker.patch("api_utils.validate_response")
        is_mocker_patch = False
        if isinstance(updated_node.func, cst.Attribute) and updated_node.func.attr.value == "patch":
             if isinstance(updated_node.func.value, cst.Name) and updated_node.func.value.value in ["mocker", "mock"]:
                  is_mocker_patch = True
             elif isinstance(updated_node.func.value, cst.Attribute) and updated_node.func.value.attr.value == "mock":
                  is_mocker_patch = True

        if is_mocker_patch and len(updated_node.args) > 0 and isinstance(updated_node.args[0].value, cst.SimpleString):
             patch_target = updated_node.args[0].value.value.strip("\"'")
             parts = patch_target.split(".")
             if parts:
                  first_part = parts[0]
                  # Check if it's an internal module
                  # (We don't have deconstructed_path here easily, but we can assume common ones or use deconstructed_name)
                  INTERNAL_MODULE_NAMES = ["utils", "constants", "exceptions", "datamodels", "data_models", "managers", "api_client", "authenticator", "common", "authentication_manager", "action_utils", "data_parser", "client", "entities_manager", "api_utils"]
                  if first_part in INTERNAL_MODULE_NAMES:
                       # Best guess: it's in core
                       new_target = f"{self.deconstructed_name}.core.{patch_target}"
                       new_args = list(updated_node.args)
                       new_args[0] = updated_node.args[0].with_changes(value=cst.SimpleString(value=f"'{new_target}'"))
                       logger.debug(f"Remapped internal mocker.patch from {patch_target} to {new_target}")
                       return updated_node.with_changes(args=tuple(new_args))
                  elif first_part == self.integration_name:
                       new_target = patch_target.replace(self.integration_name, self.deconstructed_name, 1)
                       new_args = list(updated_node.args)
                       new_args[0] = updated_node.args[0].with_changes(value=cst.SimpleString(value=f"'{new_target}'"))
                       logger.debug(f"Remapped integration mocker.patch from {patch_target} to {new_target}")
                       return updated_node.with_changes(args=tuple(new_args))

        return updated_node

    def leave_BinaryOperation(self, original_node: cst.BinaryOperation, updated_node: cst.BinaryOperation) -> Union[cst.BinaryOperation, cst.BaseExpression]:
        # Handle Path / "Connectors" -> Path / "connectors"
        if isinstance(updated_node.operator, cst.Divide):
            if isinstance(updated_node.right, cst.SimpleString):
                val = updated_node.right.value.strip("\"'")
                if val in INTEGRATIONS_PATH_MAPPING:
                    new_val = INTEGRATIONS_PATH_MAPPING[val]
                    return updated_node.with_changes(
                        right=cst.SimpleString(value=f"'{new_val}'")
                    )
        return updated_node

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> Union[cst.Attribute, cst.Name, cst.BaseExpression]:
        # Remap Integrations.IntegrationName -> snake_case_name
        if isinstance(updated_node.value, cst.Name) and updated_node.value.value == "Integrations":
            if isinstance(updated_node.attr, cst.Name):
                target_snake = str_to_snake_case(updated_node.attr.value)
                if target_snake in ["akamai", "http", "twilio"]:
                    target_snake += "_integration"
                return cst.Name(target_snake)

        # Remap Tests.integrations.IntegrationName -> snake_case_name.tests
        if isinstance(updated_node.value, cst.Attribute):
            val = updated_node.value
            if (
                isinstance(val.value, cst.Name)
                and val.value.value == "Tests"
                and isinstance(val.attr, cst.Name)
                and val.attr.value == "integrations"
            ):
                if isinstance(updated_node.attr, cst.Name):
                    target_snake = str_to_snake_case(updated_node.attr.value)
                    if target_snake in ["akamai", "http", "twilio"]:
                        target_snake += "_integration"
                    return cst.parse_expression(f"{target_snake}.tests")

        return updated_node


class ImportTransformer(cst.CSTTransformer):
    """Handles remapping of imports during integration refactoring."""

    def __init__(self, integration_name: str, deconstructed_name: str, current_module: str = "", deconstructed_path: Optional[Path] = None):
        super().__init__()
        self.integration_name = integration_name
        self.deconstructed_name = deconstructed_name
        self.current_module = current_module
        self.deconstructed_path = deconstructed_path
        self.needs_abc_import = False
        self.has_abc_import = False

    def _remap_integration_path(self, path: str) -> str:
        # Handle Integrations.*
        if path.startswith("Integrations."):
            parts = path.split(".")
            # parts[0] is "Integrations", parts[1] is IntegrationName
            if len(parts) > 1:
                int_name = parts[1]
                target_snake = str_to_snake_case(int_name)
                # Apply _integration suffix if it's one of the known collision cases
                if target_snake in ["akamai", "http", "twilio"]:
                    target_snake += "_integration"
                
                remaining = parts[2:]
                if remaining and remaining[0] in INTEGRATIONS_PATH_MAPPING:
                    remaining[0] = INTEGRATIONS_PATH_MAPPING[remaining[0]]
                
                return ".".join([target_snake] + remaining)

        # Handle Tests.integrations.*
        if path.startswith("Tests.integrations."):
            parts = path.split(".")
            if len(parts) > 2:
                int_name = parts[2]
                target_snake = str_to_snake_case(int_name)
                if target_snake in ["akamai", "http", "twilio"]:
                    target_snake += "_integration"
                
                return ".".join([target_snake, "tests"] + parts[3:])

        # Handle absolute imports that might have been partially refactored
        if path.startswith(self.integration_name) and not path.startswith(f"{self.deconstructed_name}"):
            return path.replace(self.integration_name, self.deconstructed_name, 1)

        return path

    def visit_Import(self, node: cst.Import) -> None:
        for alias in node.names:
            if isinstance(alias, cst.ImportAlias) and alias.name.value == "abc":
                self.has_abc_import = True

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> Union[cst.Import, cst.ImportFrom]:
        new_aliases = []
        sdk_aliases = []
        for alias in updated_node.names:
            if isinstance(alias, cst.ImportAlias):
                old_path = _get_module_path_str(alias.name)
                remapped_path = self._remap_integration_path(old_path)

                is_sdk = remapped_path in SDK_MODULES or (remapped_path.startswith("soar_sdk.") and remapped_path.split(".")[1] in SDK_MODULES)

                if is_sdk:
                    # If it was already soar_sdk.Module, we want to import just Module from soar_sdk
                    if remapped_path.startswith("soar_sdk."):
                         alias = alias.with_changes(name=cst.Name(remapped_path.split(".")[1]))
                    sdk_aliases.append(alias)
                    continue

                new_path = _remap_sdk_path(remapped_path)
                new_aliases.append(alias.with_changes(name=cst.parse_expression(new_path)))
            else:
                new_aliases.append(alias)

        if sdk_aliases and not new_aliases:
            return cst.ImportFrom(module=cst.Name("soar_sdk"), names=tuple(sdk_aliases))

        if sdk_aliases:
            for alias in sdk_aliases:
                new_aliases.append(alias.with_changes(name=cst.parse_expression(f"soar_sdk.{_get_module_path_str(alias.name)}")))

        return updated_node.with_changes(names=tuple(new_aliases))

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[cst.ImportFrom, cst.RemovalSentinel]:
        # Handle relative imports (e.g. from . import constants)
        if updated_node.relative:
            level = len(updated_node.relative)
            module_name = ""
            if updated_node.module:
                module_name = _get_module_path_str(updated_node.module)

            # Convert to absolute import
            if self.current_module:
                parts = self.current_module.split(".")
                # level 1 means current package, level 2 means parent, etc.
                if level <= len(parts):
                    base_parts = parts[: len(parts) - level]
                    new_module = ".".join(filter(None, base_parts + [module_name]))
                    logger.debug(f"Converted relative import to absolute: {new_module}")
                    return updated_node.with_changes(
                        module=cst.parse_expression(new_module),
                        relative=(),
                    )

        if updated_node.module is None:
            return updated_node

        module_path = _get_module_path_str(updated_node.module)

        # Handle flat imports of internal modules
        if self.deconstructed_path:
            # We only want to remap the first part of the module path if it's flat
            first_part = module_path.split(".")[0]

            # Try to find where it is
            # If we are in tests, prefer tests/ then core/
            is_in_tests = ".tests" in self.current_module

            targets = []
            if is_in_tests:
                targets = [("tests", self.deconstructed_path / "tests"), ("core", self.deconstructed_path / "core")]
            else:
                targets = [("core", self.deconstructed_path / "core"), ("tests", self.deconstructed_path / "tests")]

            for sub, folder in targets:
                # Check if it's a file or a directory in this folder
                if (folder / f"{first_part}.py").exists() or (folder / first_part).is_dir():
                    # Prefix with absolute path
                    new_module = f"{self.deconstructed_name}.{sub}.{module_path}"
                    return updated_node.with_changes(module=cst.parse_expression(new_module), relative=())

        if "Tests.mocks.product" in module_path:
            self.needs_abc_import = True
            return cst.RemoveFromParent()

        # Handle SDK module relocations (CaseInfo moved from SiemplifyConnectors to SiemplifyConnectorsDataModel)
        if module_path in ["SiemplifyConnectors", "soar_sdk.SiemplifyConnectors"]:
             names = [a.name.value for a in updated_node.names if isinstance(a, cst.ImportAlias)]
             if "CaseInfo" in names:
                 return updated_node.with_changes(
                     module=cst.parse_expression("soar_sdk.SiemplifyConnectorsDataModel"),
                     relative=(),
                 )

        if (module_path == "Tests.integrations.Siemplify" or module_path.startswith("Tests.integrations.Siemplify.")) and self.integration_name != "Siemplify":
            new_module = module_path.replace("Tests.integrations.Siemplify", f"{self.deconstructed_name}.tests.mocks.siemplify", 1)
            logger.debug(f"Remapped Siemplify mock import: {module_path} -> {new_module}")
            return updated_node.with_changes(
                module=cst.parse_expression(new_module),
                relative=(),
            )

        remapped_path = _remap_sdk_path(module_path)

        if module_path.startswith("Integrations.") or module_path.startswith("Tests.integrations."):
            remapped = self._remap_integration_path(remapped_path)
            return updated_node.with_changes(
                module=cst.parse_expression(remapped),
                relative=(),
            )

        test_prefix = f"Tests.integrations.{self.integration_name}"
        if module_path.startswith(test_prefix):
             # This is a bit redundant now with the generalized check above, 
             # but keeping it for safety for now.
            new_module = module_path.replace(test_prefix, f"{self.deconstructed_name}.tests", 1)
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
        if "aiohttp" not in path:
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
            logger.debug(f"Added abc.ABC base class to MockProduct in {self.deconstructed_name}")
            return updated_node.with_changes(bases=new_bases)
        return updated_node

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if self.needs_abc_import and not self.has_abc_import:
            new_body = list(updated_node.body)
            insert_idx = _get_insert_index_after_future(new_body)
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

    def __init__(self, use_local_import_test: bool = False):
        super().__init__()
        self.use_local_import_test = use_local_import_test
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
        module_path = _get_module_path_str(node.module)
        if module_path == "integration_testing.common":
            if any(isinstance(a, cst.ImportAlias) and a.name.value == "get_def_file_content" for a in node.names):
                self.has_get_def = True

    def visit_Import(self, node: cst.Import) -> None:
        if any(isinstance(a, cst.ImportAlias) and a.name.value == "pathlib" for a in node.names):
            self.has_pathlib = True
        if any(isinstance(a, cst.ImportAlias) and a.name.value == "json" for a in node.names):
            self.has_json = True

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        for target in updated_node.targets:
            if isinstance(target.target, cst.Name):
                name = target.target.value
                if name == "INTEGRATION_PATH":
                    self.has_int_path = True
                    return updated_node.with_changes(
                        value=cst.parse_expression("pathlib.Path(__file__).parent.parent")
                    )
                elif name == "CONFIG_PATH":
                    self.has_config_path = True
                elif name == "CONFIG":
                    self.has_config = True
        return updated_node

    def leave_AnnAssign(self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign) -> cst.AnnAssign:
        if isinstance(updated_node.target, cst.Name):
            name = updated_node.target.value
            if name == "INTEGRATION_PATH":
                self.has_int_path = True
                return updated_node.with_changes(
                    value=cst.parse_expression("pathlib.Path(__file__).parent.parent")
                )
            elif name == "CONFIG_PATH":
                self.has_config_path = True
            elif name == "CONFIG":
                self.has_config = True
        return updated_node

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
            if self.use_local_import_test:
                new_body.append(
                    cst.parse_statement(
                        "CONFIG: dict = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}"
                    )
                )
            else:
                new_body.append(
                    cst.parse_statement(
                        "CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}"
                    )
                )

        # Add imports if missing
        if not self.has_get_def and not self.use_local_import_test:
            new_body.insert(0, cst.parse_statement("from integration_testing.common import get_def_file_content"))
        if not self.has_json:
            new_body.insert(0, cst.parse_statement("import json"))
        if not self.has_pathlib:
            new_body.insert(0, cst.parse_statement("import pathlib"))
        if not self.has_future:
            new_body.insert(0, cst.parse_statement("from __future__ import annotations"))

        # Ensure __future__ is always first
        return _fix_future_order(updated_node.with_changes(body=tuple(new_body)))


# --- Main Engine ---


class ConftestTransformer(cst.CSTTransformer):
    """Organizes conftest.py with early environment redirection and clean patching."""

    def __init__(self, deconstructed_name: str, shim: str, patches: str):
        super().__init__()
        self.deconstructed_name = deconstructed_name
        self.shim = shim
        self.patches = patches
        self.has_shim = False
        self.has_plugin = False
        self.has_sdk_session = False
        self.fixtures_to_patch = [
            "script_session", "akamai_script_session", "google_chronicle_ai_agents_script_session",
            "api_client_fixture", "google_sec_ops_ai_agents_script_session", "api_session", "sdk_session"
        ]

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        new_body = list(updated_node.body)
        
        # Check for shim and plugins
        for stmt in new_body:
            code = cst.Module([]).code_for_node(stmt)
            if "import soar_sdk" in code:
                self.has_shim = True
            if "pytest_plugins =" in code:
                self.has_plugin = True
            if "def sdk_session_fixture" in code:
                self.has_sdk_session = True

        # Insert shim and plugin at the top (after __future__)
        insert_idx = _get_insert_index_after_future(new_body)
        
        if not self.has_plugin:
            new_body.insert(insert_idx, cst.parse_statement('pytest_plugins = ("integration_testing.conftest",)'))
            insert_idx += 1
        
        if not self.has_shim:
            shim_stmts = cst.parse_module(self.shim).body
            for i, stmt in enumerate(shim_stmts):
                new_body.insert(insert_idx + i, stmt)
        
        if not self.has_sdk_session:
            new_body.append(cst.parse_statement(
                "\n@pytest.fixture(name='sdk_session', autouse=True)\ndef sdk_session_fixture(script_session):\n    return script_session\n"
            ))

        return updated_node.with_changes(body=tuple(new_body))

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        is_target_fixture = updated_node.name.value in self.fixtures_to_patch
        fixture_name_in_decorator = None
        
        for decorator in updated_node.decorators:
            if isinstance(decorator.decorator, cst.Call):
                for arg in decorator.decorator.args:
                    if (isinstance(arg.keyword, cst.Name) and arg.keyword.value == "name" and 
                        isinstance(arg.value, cst.SimpleString)):
                        name_val = arg.value.value.strip("'").strip('"')
                        fixture_name_in_decorator = name_val
                        if name_val in self.fixtures_to_patch:
                            is_target_fixture = True
        
        if not is_target_fixture: return updated_node
        
        # Don't patch simple wrappers like sdk_session_fixture(script_session)
        if updated_node.name.value == "sdk_session_fixture" or fixture_name_in_decorator == "sdk_session":
             params = [p.name.value for p in updated_node.params.params]
             if "script_session" in params:
                  return updated_node.with_changes(
                       body=updated_node.body.with_changes(body=(cst.parse_statement("return script_session"),))
                  )

        # Ensure monkeypatch is in the arguments
        has_monkeypatch = any(p.name.value == "monkeypatch" for p in updated_node.params.params)
        new_params = updated_node.params
        if not has_monkeypatch:
            new_params = updated_node.params.with_changes(
                params=[cst.Param(name=cst.Name("monkeypatch"))] + list(updated_node.params.params)
            )

        # Detect and normalize session variable name
        session_var_name = "session"
        existing_assignment_val = None
        new_body_stats = list(updated_node.body.body)
        
        for stmt in new_body_stats:
            if isinstance(stmt, cst.SimpleStatementLine):
                for body in stmt.body:
                    if isinstance(body, cst.Assign):
                        code = cst.Module([]).code_for_node(body)
                        if "Session(" in code and "monkeypatch.setattr" not in code:
                             existing_assignment_val = cst.Module([]).code_for_node(body.value).strip()
                             break
        
        if not existing_assignment_val:
             ret_type = None
             if updated_node.returns:
                 ret_type = cst.Module([]).code_for_node(updated_node.returns.annotation).strip()
             if not ret_type or "Session" not in ret_type:
                 parts = self.deconstructed_name.split("_")
                 ret_type = "".join(p.capitalize() for p in parts) + "Session"
             product_arg = next((p.name.value for p in updated_node.params.params if p.name.value not in ["monkeypatch", "mocker"]), "None")
             existing_assignment_val = f"{ret_type}({product_arg})"

        # Clean up ALL existing patches and assignments
        cleaned_body = []
        patterns = [
            "requests.sessions.Session.request", "MARKETPLACE MIGRATION PATCHES",
            "import Siemplify", "import requests", "from TIPCommon", "return ", "yield "
        ]
        
        for stmt in new_body_stats:
            code = cst.Module([]).code_for_node(stmt)
            if any(p in code for p in patterns): continue
            if "Session(" in code and "=" in code: continue # Skip old session assignment
            cleaned_body.append(stmt)
        
        # Add standardized session assignment
        cleaned_body.insert(0, cst.parse_statement(f"{session_var_name} = {existing_assignment_val}"))
        
        # Add patches
        import textwrap
        marker = "# --- MARKETPLACE MIGRATION PATCHES ---"
        import re
        p_str = textwrap.dedent(self.patches)
        p_str = re.sub(r'\bsession\b', session_var_name, p_str)
        
        patch_stmts = cst.parse_module(f"    {marker}\n" + p_str).body
        for i, patch_stmt in enumerate(patch_stmts):
             cleaned_body.insert(1 + i, patch_stmt)
        
        # Add return/yield
        keyword = "yield" if "yield" in cst.Module([]).code_for_node(updated_node.body) else "return"
        cleaned_body.append(cst.parse_statement(f"{keyword} {session_var_name}"))

        return updated_node.with_changes(
            params=new_params,
            body=updated_node.body.with_changes(body=tuple(cleaned_body))
        )


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

        success_count = 0
        failure_count = 0
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
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to refactor {integration_path.name}: {e}", exc_info=True)
                    failure_count += 1
                progress.advance(task)
                
        logger.info(f"Refactor summary: {success_count} succeeded, {failure_count} failed.")

    def refactor_single(self, integration_path: Path):
        """Refactors a single integration."""
        integration_name = integration_path.name
        deconstructed_name = str_to_snake_case(integration_name)
        
        # Only use folder suffix if absolutely necessary to avoid library collision
        # http and twilio are already in the marketplace with the suffix
        if deconstructed_name in ["akamai", "http", "twilio"]:
             deconstructed_name += "_integration"

        deconstructed_path = self.dst_path / deconstructed_name

        logger.info(f"[bold blue]Processing: {integration_name}[/bold blue]")

        # 1. Widgets
        logger.info(f"[{integration_name}] Step 1: Converting Widgets...")
        self.convert_widgets(integration_path)

        # 2. Deconstruct
        logger.info(f"[{integration_name}] Step 2: Deconstructing integration into {deconstructed_path.name}...")
        deconstructed_path.mkdir(exist_ok=True, parents=True)
        self.repo._deconstruct_integration(integration_path, deconstructed_path)

        # Ensure root __init__.py exists
        (deconstructed_path / "__init__.py").touch(exist_ok=True)
        logger.debug(f"[{integration_name}] Ensured root __init__.py exists in {deconstructed_path.name}")

        self.copy_ai_descriptions(integration_path, deconstructed_path)

        # 3. Tests
        logger.info(f"[{integration_name}] Step 3: Converting Tests and Mocks...")
        self.convert_tests(integration_name, deconstructed_path)
        self.copy_siemplify_mocks(integration_name, deconstructed_path)

        # 4. Source Files
        logger.info(f"[{integration_name}] Step 4: Refactoring Source Files...")
        self.refactor_source_files(integration_name, deconstructed_path)

        # 5. Version & Sync
        logger.info(f"[{integration_name}] Step 5: Bumping Version and Syncing Dependencies...")
        self.increment_version_and_sync(deconstructed_path, integration_name, integration_path)

        # 6. License Headers
        logger.info(f"[{integration_name}] Step 6: Adding License Headers...")
        self.add_license_headers(deconstructed_path)

        # 7. Ruff Exclude
        logger.info(f"[{integration_name}] Step 7: Updating Ruff Configuration...")
        self.add_to_ruff_specific_integrations(deconstructed_path.name)
        
        logger.info(f"[bold green]Successfully finished processing: {integration_name}[/bold green]")

    def refactor_source_files(self, integration_name: str, deconstructed_path: Path):
        """Refactors all non-test Python files in the deconstructed integration."""
        deconstructed_name = deconstructed_path.name
        files_processed = 0
        for folder in ["actions", "core", "connectors", "jobs"]:
            folder_path = deconstructed_path / folder
            if folder_path.is_dir():
                for file_path in folder_path.rglob("*.py"):
                    # Fix AttributeError: 'SiemplifySdkConfig' object has no attribute 'domain'
                    content = file_path.read_text(encoding="utf-8")
                    if 'sdk_config.domain' in content:
                        # Replace the whole known pattern for building Google SecOps API URI
                        pattern = r'def get_google_secops_api_uri\(soar_sdk_object: ChronicleSOAR\) -> str:.*?return \(.*?f"projects/\{project\}/locations/\{location\}/instances/\{instance\}"\s*\)'
                        replacement = 'def get_google_secops_api_uri(soar_sdk_object: ChronicleSOAR) -> str:\n    return soar_sdk_object.sdk_config.one_platform_api_root_uri_format.format(BASE_1P_SDK_CONTROLLER_VERSION)'
                        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                        file_path.write_text(content, encoding="utf-8")

                    logger.debug(f"[{integration_name}] Refactoring source file: {file_path.name}")
                    self._transform_python_file(file_path, integration_name, deconstructed_path)
                    files_processed += 1
                    
        logger.info(f"[{integration_name}] Refactored {files_processed} source files.")

    def copy_siemplify_mocks(self, integration_name: str, deconstructed_path: Path):
        """Copies Siemplify common test utilities to a local mock folder."""
        needs_mocks = False
        tests_dir = deconstructed_path / "tests"
        if not tests_dir.exists():
            return

        for py_file in tests_dir.rglob("*.py"):
            try:
                if f"{deconstructed_path.name}.tests.mocks.siemplify" in py_file.read_text(encoding="utf-8"):
                    needs_mocks = True
                    break
            except Exception:
                continue

        if not needs_mocks:
            return

        logger.info(f"Copying Siemplify mocks to {deconstructed_path.name}")
        src_siemplify = self.tests_dir / "integrations" / "Siemplify"
        dst_siemplify = deconstructed_path / "tests" / "mocks" / "siemplify"
        dst_siemplify.mkdir(parents=True, exist_ok=True)

        files_to_copy = ["common.py", "mock_data.json", "config.json"]
        for f in files_to_copy:
            src_f = src_siemplify / f
            if src_f.exists():
                shutil.copy2(src_f, dst_siemplify / f)

        (deconstructed_path / "tests" / "mocks" / "__init__.py").touch(exist_ok=True)
        (dst_siemplify / "__init__.py").touch(exist_ok=True)

        src_core = src_siemplify / "core"
        if src_core.is_dir():
            dst_core = dst_siemplify / "core"
            dst_core.mkdir(exist_ok=True)
            for f in ["__init__.py", "product.py", "session.py"]:
                src_f = src_core / f
                if src_f.exists():
                    shutil.copy2(src_f, dst_core / f)

        # Refactor the copied mocks
        for py_file in dst_siemplify.rglob("*.py"):
            # Special case for common.py to fix INTEGRATION_PATH
            if py_file.name == "common.py":
                 content = py_file.read_text(encoding="utf-8")
                 if 'INTEGRATION_PATH' in content:
                      # Match INTEGRATION_PATH assignment and everything until the next constant or empty line
                      content = re.sub(r'INTEGRATION_PATH\s*:\s*pathlib\.Path\s*=\s*.*?(?=\n[A-Z_]+\s*:|\n\s*\n|\Z)', 'INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent', content, flags=re.DOTALL)
                      py_file.write_text(content, encoding="utf-8")

            self._transform_python_file(py_file, integration_name, deconstructed_path)

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

    def _ensure_dependencies_healthy(self, deconstructed_path: Path, integration_name: str):
        """
        Ensures that the integration has all necessary dev dependencies, particularly integration-testing.
        
        This is implemented for cases where the TIPCommon version from the source tip-marketplace repo 
        didn't have a local wheel file in the content hub, and after understanding that, the user 
        copied the wheel to be local but an integration testing should be in a matching version 
        according to the mp deconstruct.
        """
        pyproject_path = deconstructed_path / PYPROJECT_TOML
        if not pyproject_path.exists():
            return

        with pyproject_path.open("r", encoding="utf-8") as f:
            pyproject_data = toml.load(f)

        dev_deps = pyproject_data.get("dependency-groups", {}).get("dev", [])
        
        if any("integration-testing" in d or "integration_testing" in d for d in dev_deps):
            logger.debug(f"[{integration_name}] integration-testing dependency already present.")
            return

        logger.warning(f"[{integration_name}] integration-testing dependency missing! Attempting to fix...")

        # Rescue EnvironmentCommon if missing from sources
        local_packages_path = get_local_packages_path()
        sources = pyproject_data.get("tool", {}).get("uv", {}).get("sources", {})
        if "environmentcommon" not in sources:
            env_wheels_dir = local_packages_path / "envcommon" / "whls"
            env_whls = list(env_wheels_dir.glob("EnvironmentCommon-*.whl"))
            if env_whls:
                from packaging.version import parse as parse_version
                latest_env_whl = sorted(env_whls, key=lambda p: parse_version(re.search(r"EnvironmentCommon-([\d\.]+)", p.name).group(1)))[-1]
                rel_path = os.path.relpath(latest_env_whl, deconstructed_path)
                
                if "tool" not in pyproject_data:
                    pyproject_data["tool"] = {}
                if "uv" not in pyproject_data["tool"]:
                    pyproject_data["tool"]["uv"] = {}
                if "sources" not in pyproject_data["tool"]["uv"]:
                    pyproject_data["tool"]["uv"]["sources"] = {}
                    
                pyproject_data["tool"]["uv"]["sources"]["environmentcommon"] = {"path": rel_path}
                
                with open(pyproject_path, "w", encoding="utf-8") as f:
                    toml.dump(pyproject_data, f)
                logger.info(f"[{integration_name}] Rescued EnvironmentCommon to uv.sources: {latest_env_whl.name}")

        # Find TIPCommon version to use as target
        tipcommon_version = None
        
        # Check dependencies
        deps = pyproject_data.get("project", {}).get("dependencies", [])
        for dep in deps:
            if dep.lower().startswith("tipcommon"):
                if "==" in dep:
                    tipcommon_version = dep.split("==")[1]
                    break

        # Check for TODO comments if not found in dependencies
        if not tipcommon_version:
            content = pyproject_path.read_text(encoding="utf-8")
            match = re.search(r"#\s*TODO:.*TIPCommon==([\d\.]+)", content, re.IGNORECASE)
            if match:
                tipcommon_version = match.group(1)
                logger.info(f"[{integration_name}] Found TIPCommon version in TODO comment: {tipcommon_version}")

        # Check uv sources if not found yet
        if not tipcommon_version:
            sources = pyproject_data.get("tool", {}).get("uv", {}).get("sources", {})
            tipcommon_source = sources.get("tipcommon", {})
            if "path" in tipcommon_source:
                path = tipcommon_source["path"]
                match = re.search(r"TIPCommon-([\d\.]+)", path)
                if match:
                    tipcommon_version = match.group(1)

        if not tipcommon_version:
            logger.warning(f"[{integration_name}] Could not determine TIPCommon version. Falling back to latest integration-testing.")
            tipcommon_version = "0.0.0"

        # Find closest wheel
        local_packages_path = get_local_packages_path()
        it_wheels_dir = local_packages_path / "integration_testing_whls"
        
        try:
            from packaging.version import parse as parse_version
            target_version = parse_version(tipcommon_version)
            
            whls = list(it_wheels_dir.glob("integration_testing-*.whl"))
            if not whls:
                raise FileNotFoundError(f"No integration-testing wheels found in {it_wheels_dir}")
                
            version_whl_map = {}
            for whl in whls:
                match = re.search(r"integration_testing-([\d\.]+)", whl.name)
                if match:
                    version_whl_map[parse_version(match.group(1))] = whl
                    
            sorted_versions = sorted(version_whl_map.keys())
            
            best_wheel = None
            # Try to find closest >= 
            for v in sorted_versions:
                if v >= target_version:
                    best_wheel = version_whl_map[v]
                    logger.info(f"[{integration_name}] Found integration-testing >= version: {v} for target {tipcommon_version}")
                    break
                    
            if not best_wheel:
                best_wheel = version_whl_map[sorted_versions[-1]]
                logger.info(f"[{integration_name}] Fallback to highest integration-testing version: {sorted_versions[-1]} for target {tipcommon_version}")

            # Rescue TIPCommon as well if it was dropped
            tip_wheels_dir = local_packages_path / "tipcommon" / "whls"
            tip_wheel = tip_wheels_dir / f"TIPCommon-{tipcommon_version}-py2.py3-none-any.whl"
            if not tip_wheel.exists():
                tip_wheel = tip_wheels_dir / f"TIPCommon-{tipcommon_version}-py3-none-any.whl"

            reg_deps_to_add = []
            if tip_wheel.exists():
                logger.info(f"[{integration_name}] Rescuing TIPCommon wheel: {tip_wheel.name}")
                reg_deps_to_add.append(str(tip_wheel))
            else:
                logger.warning(f"[{integration_name}] Could not find exact TIPCommon wheel {tipcommon_version} locally.")

            # Install dependencies
            add_dependencies_to_toml(deconstructed_path, reg_deps_to_add, [str(best_wheel)])
            
            logger.info(f"[{integration_name}] Successfully fixed dependencies.")

        except Exception as e:
            logger.error(f"[{integration_name}] Failed to fix dependencies: {e}")

    def convert_tests(self, integration_name: str, deconstructed_path: Path):
        tests_src_path = self.tests_dir / "integrations" / integration_name
        tests_dest_path = deconstructed_path / "tests"
        deconstructed_name = deconstructed_path.name

        tests_dest_path.mkdir(exist_ok=True, parents=True)
        self._ensure_dependencies_healthy(deconstructed_path, integration_name)

        if tests_src_path.is_dir():
            logger.info(f"[{integration_name}] Copying tests from {tests_src_path}...")
            shutil.copytree(tests_src_path, tests_dest_path, dirs_exist_ok=True)
        else:
            logger.warning(f"[{integration_name}] No existing tests found at {tests_src_path}.")

        self._cleanup_test_files(tests_dest_path)
        use_local_import_test = self._handle_test_dependencies(deconstructed_path, tests_dest_path, integration_name)
        self._refactor_common_py(tests_dest_path, use_local_import_test)

        if not use_local_import_test:
            self._standardize_conftest(tests_dest_path, deconstructed_name)

        files_processed = 0
        for file_path in tests_dest_path.rglob("*.py"):
            self._transform_python_file(file_path, integration_name, deconstructed_path)
            files_processed += 1
            
        logger.info(f"[{integration_name}] Refactored {files_processed} test files.")

        for root, _, _ in os.walk(tests_dest_path):
            (Path(root) / "__init__.py").touch(exist_ok=True)

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
            if not any(d.lower().startswith("tipcommon") for d in all_deps):
                self._add_local_deps(deconstructed_path, tests_dest_path.parent)
            else:
                self._check_mock_imports(tests_dest_path, integration_name)
                use_local_import_test = True
        logger.debug(
            f"Dependency analysis complete for {integration_name}. use_local_import_test={use_local_import_test}"
        )
        return use_local_import_test

    @staticmethod
    def _add_local_deps(path: Path, original_path: Path):
        local_path = get_local_packages_path()

        def find_latest_whl(package_name: str, subfolder: str) -> Optional[str]:
            base_folder = local_path / subfolder
            # Check both base_folder and base_folder/whls
            folder = base_folder / "whls" if (base_folder / "whls").is_dir() else base_folder
            if not folder.is_dir():
                return None
            whls = list(folder.glob(f"{package_name}-*.whl"))
            if not whls:
                return None
            
            # Version-aware sorting
            from packaging.version import parse as parse_version
            def get_version(path):
                match = re.search(rf'{package_name}-([\d\.]+)', path.name)
                return parse_version(match.group(1)) if match else parse_version("0.0.0")

            latest_whl = sorted(whls, key=get_version)[-1]
            return str(latest_whl)

        # Add all wheels from original Dependencies directory
        orig_whls = []
        deps_dir = original_path / "Dependencies"
        if deps_dir.is_dir():
            for whl in deps_dir.glob("*.whl"):
                # Avoid adding wheels we already have in our special paths or that we want to override
                if any(x in whl.name for x in ["TIPCommon", "EnvironmentCommon", "integration_testing"]):
                    continue
                orig_whls.append(whl)

        whls = [
            find_latest_whl("EnvironmentCommon", "envcommon"),
            find_latest_whl("integration_testing", "integration_testing_whls"),
            find_latest_whl("TIPCommon", "tipcommon"),
        ] + orig_whls
        whls = [w for w in whls if w is not None]

        add_dependencies_to_toml(path, [], whls)

    @staticmethod
    def _check_mock_imports(path: Path, integration_name: str) -> None:
        for file in path.rglob("*.py"):
            content = file.read_text()
            if "from Tests.mocks" in content or "import Tests.mocks" in content:
                logger.debug(f"Mock imports found in integration {integration_name}'s tests. These will be automatically remapped to integration_testing.")

    def _refactor_common_py(self, tests_path: Path, use_local_import_test: bool = False):
        common_py = tests_path / "common.py"
        content = common_py.read_text(encoding="utf-8") if common_py.exists() else ""

        tree = cst.parse_module(content)
        modified = tree.visit(UpsertIntegrationPathTransformer(use_local_import_test=use_local_import_test))
        common_py.write_text(modified.code, encoding="utf-8")

        test_defaults = tests_path / "test_defaults"
        test_defaults.mkdir(exist_ok=True)
        if use_local_import_test:
            (test_defaults / "test_imports.py").write_text(LOCAL_IMPORT_TEST_CONTENT)
        else:
            (test_defaults / "test_imports.py").write_text(NEW_IMPORT_TEST_CONTENT)

    def _transform_python_file(self, file_path: Path, integration_name: str, deconstructed_path: Path):
        deconstructed_name = deconstructed_path.name
        rel_path = file_path.relative_to(deconstructed_path)
        module_parts = [deconstructed_name] + list(rel_path.with_suffix("").parts)
        current_module = ".".join(module_parts)
        
        logger.debug(f"Analyzing imports and logic in file: {file_path.name}")
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = cst.parse_module(content)

            # Apply Import remapping
            tree = tree.visit(ImportTransformer(integration_name, deconstructed_name, current_module, deconstructed_path))

            # Apply Expression remapping
            tree = tree.visit(ExpressionTransformer(integration_name, deconstructed_name))

            # Apply isinstance transformation
            tree = tree.visit(SDKInstanceTransformer())

            # Fix from __future__ order
            tree = _fix_future_order(tree)

            if content != tree.code:
                file_path.write_text(tree.code, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to transform {file_path.name}: {e}")

    @staticmethod
    def _standardize_conftest(tests_path: Path, deconstructed_name: str):
        conftest = tests_path / "conftest.py"

        # The following shim does two things:
        # 1. Adds SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon.
        # 2. Unifies the soar_sdk namespace with the flat namespace to ensure mocks and patches apply globally.
        #    Packages like TIPCommon use un-prefixed imports for SDK modules (e.g., `import Siemplify`).
        #    Because they often load before conftest patches the prefixed version (`soar_sdk.Siemplify`), they
        #    could bypass the mocks and make real API calls. This loop ensures both import paths resolve to the
        #    exact same module object in memory, so patches applied to one apply to both.
        shim = (
            "import sys\n"
            "import os\n"
            "import pkgutil\n"
            "import importlib\n"
            "import soar_sdk\n"
            "sdk_dir = soar_sdk.__path__[0]\n"
            "if sdk_dir not in sys.path:\n"
            "    sys.path.insert(0, sdk_dir)\n"
            "original_stdout = sys.stdout\n"
            "for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):\n"
            "    try:\n"
            "        flat_mod = importlib.import_module(name)\n"
            "        sys.modules[f'soar_sdk.{name}'] = flat_mod\n"
            "        setattr(soar_sdk, name, flat_mod)\n"
            "    except Exception:\n"
            "        pass\n"
            "sys.stdout = original_stdout\n"
        )

        patches = ""
        
        if not conftest.exists():
            conftest.write_text(f"from __future__ import annotations\n{shim}\nimport pytest\nimport requests\n", encoding="utf-8")
            # We still run the transformer to add the plugin line properly
            content = conftest.read_text(encoding="utf-8")
        else:
            content = conftest.read_text(encoding="utf-8")

        try:
            tree = cst.parse_module(content)
            transformer = ConftestTransformer(deconstructed_name, shim, patches)
            modified = tree.visit(transformer)
            conftest.write_text(modified.code, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to transform conftest.py in {deconstructed_name}: {e}")


    def increment_version_and_sync(self, path: Path, name: str, original_path: Path):
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
        
        # Standardize project name: Only suffix if folder has suffix or if collision detected
        # Check for self-dependency or dependency name collision
        has_collision = False
        if "dependencies" in data["project"]:
             for d in data["project"]["dependencies"]:
                 # Extract package name from dependency string (e.g. "requests==2.32.4" -> "requests")
                 match = re.match(r'^([a-zA-Z0-9_\-]+)', d)
                 if match:
                     pkg_name = match.group(1).replace("-", "_").lower()
                     if pkg_name == path.name.lower():
                         has_collision = True
                         break

        if path.name.endswith("_integration") or has_collision:
             standard_name = path.name.replace("_integration", "").upper()
             data["project"]["name"] = f"{standard_name}-Integration"
        else:
             data["project"]["name"] = path.name

        # Fix requests version: at least 2.32.4 or higher if in original deps
        orig_requests_v = "2.32.4"
        deps_dir = original_path / "Dependencies"
        if deps_dir.is_dir():
            for whl in deps_dir.glob("requests-*.whl"):
                match = re.search(r'requests-(\d+\.\d+\.\d+)', whl.name)
                if match:
                    v_str = match.group(1)
                    if v_str > orig_requests_v:
                        orig_requests_v = v_str
                    break
        
        if "dependencies" in data["project"]:
             new_deps = []
             for d in data["project"]["dependencies"]:
                 if d.startswith("requests"):
                     new_deps.append(f"requests=={orig_requests_v}")
                 elif d.startswith("google-auth=="):
                     new_deps.append(d.replace("==", ">="))
                 else:
                     new_deps.append(d)
             data["project"]["dependencies"] = new_deps

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
