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
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import libcst as cst
from libcst import FlattenSentinel
from libcst.helpers import get_full_name_for_node

from . import constants, file_utils, unix
from .constants import SDK_MODULES

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .custom_types import RuffParams

SDK_PREFIX: str = f"{constants.SDK_PACKAGE_NAME}."
CORE_PREFIX: str = f"{constants.CORE_SCRIPTS_DIR}."


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


class FutureAnnotationsTransformer(cst.CSTTransformer):
    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:  # noqa: N802, PLR6301
        """Ensure `from __future__ import annotations` is present at the top of the module.

        Returns:
            The updated module with `from __future__ import annotations` at the top.

        """
        if not original_node.body:
            return updated_node

        import_annotations_statement = cst.parse_statement("from __future__ import annotations")

        # Check if the import already exists in the module.
        if any(stmt.deep_equals(import_annotations_statement) for stmt in original_node.body):
            return updated_node

        new_body = list(updated_node.body)
        insert_pos = 0

        # Find the position after the docstring and any leading comments.
        if new_body and isinstance(new_body[0], cst.SimpleStatementLine):
            statement_body = new_body[0].body
            if (
                statement_body
                and isinstance(statement_body[0], cst.Expr)
                and isinstance(statement_body[0].value, cst.SimpleString)
            ):
                insert_pos = 1

        new_body.insert(insert_pos, import_annotations_statement)
        return updated_node.with_changes(body=tuple(new_body))


class SdkImportTransformer(cst.CSTTransformer):
    def leave_ImportFrom(  # noqa: N802, PLR6301
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for SDK modules.

        Returns:
            The transformed node.

        """
        if original_node.module is None:
            return updated_node

        if not (full_module_name := get_full_name_for_node(original_node.module)):
            return updated_node

        first_module_part = full_module_name.split(".", maxsplit=1)[0]
        if first_module_part in SDK_MODULES and not full_module_name.startswith(SDK_PREFIX):
            prefixed_module = _create_prefixed_module(full_module_name, SDK_PREFIX)
            return updated_node.with_changes(module=prefixed_module)

        return updated_node

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:  # noqa: ARG002, N802, PLR6301
        """Transform `import <module>` statements for SDK modules.

        Returns:
            The transformed node.

        """
        new_aliases = []
        changed = False

        for alias in updated_node.names:
            if (
                (full_module_name := get_full_name_for_node(alias.name))
                and full_module_name.split(".", maxsplit=1)[0] in SDK_MODULES
                and not full_module_name.startswith(SDK_PREFIX)
            ):
                prefixed_module = _create_prefixed_module(full_module_name, SDK_PREFIX)
                new_aliases.append(alias.with_changes(name=prefixed_module))
                changed = True
            else:
                new_aliases.append(alias)

        return updated_node.with_changes(names=tuple(new_aliases)) if changed else updated_node


class BaseCoreImportTransformer(cst.CSTTransformer, ABC):
    """Base transformer for handling core package imports."""

    def __init__(self, core_module_names: set[str]) -> None:
        super().__init__()
        self.core_module_names = core_module_names

    @abstractmethod
    def _is_core_alias(self, full_module_name: str) -> bool:
        """Determine if a module name is a core module."""

    @staticmethod
    @abstractmethod
    def _create_core_import_from(aliases: tuple[cst.ImportAlias, ...]) -> cst.ImportFrom:
        """Create the specific 'from ... import' node for core aliases."""

    def leave_SimpleStatementLine(  # noqa: N802
        self,
        original_node: cst.SimpleStatementLine,  # noqa: ARG002
        updated_node: cst.SimpleStatementLine,
    ) -> FlattenSentinel[cst.SimpleStatementLine] | cst.SimpleStatementLine:
        """Handle `import <module>` statements.

        Common logic to split imports into core and non-core statements.

        Returns:
            The updated node, which could be a single statement or a sentinel
            for multiple statements.

        """
        if not isinstance(updated_node.body[0], cst.Import):
            return updated_node

        import_statement = updated_node.body[0]
        core_aliases, non_core_aliases = self._partition_aliases(import_statement.names)

        if not core_aliases:
            return updated_node

        new_statements = []
        if non_core_aliases:
            # Preserve non-core imports
            non_core_aliases[-1] = non_core_aliases[-1].with_changes(
                comma=cst.MaybeSentinel.DEFAULT
            )
            new_statements.append(
                cst.SimpleStatementLine(
                    body=[import_statement.with_changes(names=tuple(non_core_aliases))]
                )
            )

        # Transform core imports using the subclass-specific node creator
        core_aliases[-1] = core_aliases[-1].with_changes(comma=cst.MaybeSentinel.DEFAULT)
        new_statements.append(
            cst.SimpleStatementLine(body=[self._create_core_import_from(tuple(core_aliases))])
        )

        return FlattenSentinel(new_statements)

    def _partition_aliases(
        self, aliases: Iterable[cst.ImportAlias]
    ) -> tuple[list[cst.ImportAlias], list[cst.ImportAlias]]:
        """Split import aliases into core and non-core lists.

        Args:
            aliases: An iterable of import aliases to partition.

        Returns:
            A tuple containing two lists: core aliases and non-core aliases.

        """
        core_aliases = []
        non_core_aliases = []
        for alias in aliases:
            if (full_module_name := get_full_name_for_node(alias.name)) and self._is_core_alias(
                full_module_name
            ):
                core_aliases.append(alias)
            else:
                non_core_aliases.append(alias)
        return core_aliases, non_core_aliases


class CorePackageImportTransformer(BaseCoreImportTransformer):
    def _is_core_alias(self, full_module_name: str) -> bool:
        return full_module_name in self.core_module_names

    @staticmethod
    def _create_core_import_from(aliases: tuple[cst.ImportAlias, ...]) -> cst.ImportFrom:
        # Transforms: import manager -> from ..core import manager
        return cst.ImportFrom(
            module=cst.Name("core"),
            names=aliases,
            relative=(cst.Dot(), cst.Dot()),
        )

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for core package modules.

        Returns:
            The transformed `ImportFrom` node.

        """
        if original_node.relative or original_node.module is None:
            return updated_node

        if not (full_module_name := get_full_name_for_node(original_node.module)):
            return updated_node

        if full_module_name.split(".", maxsplit=1)[0] in self.core_module_names:
            prefixed_module = _create_prefixed_module(full_module_name, CORE_PREFIX)
            return updated_node.with_changes(
                module=prefixed_module, relative=(cst.Dot(), cst.Dot())
            )

        return updated_node


class CorePackageInternalImportTransformer(BaseCoreImportTransformer):
    def __init__(self, core_module_names: set[str], current_module_name: str) -> None:
        super().__init__(core_module_names)
        self.current_module_name = current_module_name

    def _is_core_alias(self, full_module_name: str) -> bool:
        return (
            full_module_name in self.core_module_names
            and full_module_name != self.current_module_name
        )

    @staticmethod
    def _create_core_import_from(aliases: tuple[cst.ImportAlias, ...]) -> cst.ImportFrom:
        # Transforms: import manager -> from . import manager
        return cst.ImportFrom(
            module=None,
            names=aliases,
            relative=(cst.Dot(),),
        )

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for internal core package modules.

        Returns:
            The transformed `ImportFrom` node.

        """
        if original_node.relative or original_node.module is None:
            return updated_node

        if not (full_module_name := get_full_name_for_node(original_node.module)):
            return updated_node

        if (
            full_module_name in self.core_module_names
            and full_module_name != self.current_module_name
        ):
            return updated_node.with_changes(relative=(cst.Dot(),))

        return updated_node


def _create_prefixed_module(full_module_name: str, prefix: str) -> cst.Attribute | cst.Name:
    new_module_name: str = f"{prefix}{full_module_name}"
    expression: cst.BaseExpression = cst.parse_expression(new_module_name)
    if not isinstance(expression, cst.Attribute | cst.Name):
        msg: str = f"Expected 'Attribute' or 'Name', but got {type(expression).__name__}"
        raise TypeError(msg)
    return expression


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


class ImportTransformer(cst.CSTTransformer):
    def leave_Import(  # noqa: N802, PLR6301
        self,
        original_node: cst.Import,  # noqa: ARG002
        updated_node: cst.Import,
    ) -> cst.Import:
        """Handle `import <module>` statements for SDK modules.

        Transforms: import soar_sdk.module -> import module

        Returns:
            The transformed node.

        """
        new_aliases = []
        changed = False

        for alias in updated_node.names:
            if (
                full_module_name := get_full_name_for_node(alias.name)
            ) and full_module_name.startswith(SDK_PREFIX):
                new_module_name = full_module_name.removeprefix(SDK_PREFIX)
                expression = cst.parse_expression(new_module_name)
                if not isinstance(expression, cst.Name | cst.Attribute):
                    new_aliases.append(alias)
                    continue

                new_aliases.append(alias.with_changes(name=expression))
                changed = True
            else:
                new_aliases.append(alias)

        return updated_node.with_changes(names=tuple(new_aliases)) if changed else updated_node

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
                return cst.Import(names=names)

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
