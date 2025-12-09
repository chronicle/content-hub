"""Module for manipulating code: linting, formatting, and import restructuring."""


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

import warnings
from typing import TYPE_CHECKING

import libcst as cst

from . import constants, file_utils, unix

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .custom_types import RuffParams


class LinterWarning(RuntimeWarning):
    """Found linting issues."""


class TypeCheckerWarning(RuntimeWarning):
    """Found type check issues."""


class FormatterWarning(RuntimeWarning):
    """Found formatting issues."""


class TestWarning(RuntimeWarning):
    """Failed tests."""


def lint_python_files(paths: Iterable[Path], params: RuffParams) -> None:
    """Run a linter on python files and fix all unsafe issues."""
    paths = [p for p in paths if p.is_dir() or file_utils.is_python_file(p)]
    status_code: int = unix.ruff_check(
        paths,
        output_format=params.output_format.value,
        fix=params.fix,
        unsafe_fixes=params.unsafe_fixes,
    )
    if status_code != 0:
        msg: str = (
            "Found linting issues. Consider running `mp check --fix` "
            "and/or `mp check --fix --unsafe-fixes` to try and resolve them automatically."
        )
        warnings.warn(msg, LinterWarning, stacklevel=1)


def static_type_check_python_files(paths: Iterable[Path]) -> None:
    """Run a type checker on python files."""
    paths = [p for p in paths if p.is_dir() or file_utils.is_python_file(p)]
    status_code: int = unix.ty_check(paths)
    if status_code != 0:
        msg: str = "Found type check issues"
        warnings.warn(msg, TypeCheckerWarning, stacklevel=1)


def format_python_files(paths: Iterable[Path]) -> None:
    """Format python files."""
    paths = [p for p in paths if p.is_dir() or file_utils.is_python_file(p)]
    status_code: int = unix.ruff_format(paths)
    if status_code != 0:
        msg: str = "Found format issues"
        warnings.warn(msg, FormatterWarning, stacklevel=1)


def restructure_scripts_imports(paths: Iterable[Path]) -> None:
    """Restructure script imports in python files.

    Args:
        paths: the paths of the files to be modified.

    """
    paths = [p for p in paths if p.suffix == ".py"]
    for path in paths:
        file_utils.replace_file_content(path, replace_fn=restructure_script_imports)


def restructure_script_imports(code_string: str) -> str:
    """Restructure script imports in python files.

    Args:
        code_string: the code string to be modified.

    Returns:
        The modified code string.

    """
    tree: cst.Module = cst.parse_module(code_string)
    transformer: ImportTransformer = ImportTransformer()
    modified_tree: cst.Module = tree.visit(transformer)
    return modified_tree.code


class ImportTransformer(cst.CSTTransformer):
    def leave_ImportFrom(  # noqa: N802, PLR6301, D102
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom | cst.Import:
        # `from ...common.package...module import ...` => `from module import ...`
        # `from ...core.package...module import ...` => `from module import ...`
        # `from ...soar_sdk.package...module import ...` => `from module import ...`
        match _get_attribute_list(original_node):
            case [*attrs] if attrs and _is_reserved_node(attrs[-1]):
                return updated_node.with_changes(relative=[], module=attrs[0].attr)

        match original_node:
            # `from (.)?(nothing | reserved) import ...` => `import ...`
            case cst.ImportFrom(
                module=(
                    None
                    | cst.Name(
                        value=(
                            constants.CORE_SCRIPTS_DIR
                            | constants.COMMON_SCRIPTS_DIR
                            | constants.SDK_PACKAGE_NAME
                        ),
                    )
                ),
                names=names,
            ):
                return cst.Import(names=names)  # type: ignore[arg-type]

            # `from .module import ...` => `from module import ...`
            case cst.ImportFrom(relative=[cst.Dot(), *_]):
                return updated_node.with_changes(relative=[])

            case _:
                return updated_node


def _is_reserved_node(node: cst.Attribute) -> bool:
    return isinstance(name := node.value, cst.Name) and name.value in {
        constants.COMMON_SCRIPTS_DIR,
        constants.CORE_SCRIPTS_DIR,
        constants.SDK_PACKAGE_NAME,
    }


def _get_attribute_list(node: cst.ImportFrom) -> list[cst.Attribute]:
    nodes: list[cst.Attribute] = []
    current_node: cst.Name | cst.Attribute | None = node.module
    while isinstance(current_node, cst.Attribute):
        nodes.append(current_node)
        current_node = current_node.value  # type: ignore[assignment]

    return nodes
