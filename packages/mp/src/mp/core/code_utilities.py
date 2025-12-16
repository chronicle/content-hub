"""Module for code utilities."""


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

import libcst as cst
from libcst.helpers import get_full_name_for_node

from . import constants
from .constants import SDK_MODULES

SDK_PREFIX: str = f"{constants.SDK_PACKAGE_NAME}."
CORE_PREFIX: str = f"{constants.CORE_SCRIPTS_DIR}."


def _create_prefixed_module(full_module_name: str, prefix: str) -> cst.Attribute | cst.Name:
    new_module_name: str = f"{prefix}{full_module_name}"
    expression: cst.BaseExpression = cst.parse_expression(new_module_name)
    if not isinstance(expression, cst.Attribute | cst.Name):
        msg: str = f"Expected 'Attribute' or 'Name', but got {type(expression).__name__}"
        raise TypeError(msg)
    return expression


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
        # A docstring is the first statement if it's an expression containing a string.
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
            The updated `ImportFrom` node with SDK modules prefixed.

        """
        if original_node.module is None:
            return updated_node

        full_module_name: str | None = get_full_name_for_node(original_node.module)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in SDK_MODULES and not full_module_name.startswith(SDK_PREFIX):
            prefixed_module = _create_prefixed_module(full_module_name, SDK_PREFIX)
            return updated_node.with_changes(module=prefixed_module)

        return updated_node

    def leave_Import(self, original_node: cst.Import, updated_node: cst.Import) -> cst.Import:  # noqa: N802, PLR6301
        """Transform `import <module>` statements for SDK modules.

        Returns:
            The updated `Import` node with SDK modules prefixed.

        """
        full_module_name: str | None = get_full_name_for_node(original_node.names[0].name)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in SDK_MODULES and not full_module_name.startswith(SDK_PREFIX):
            prefixed_module = _create_prefixed_module(full_module_name, SDK_PREFIX)
            return updated_node.with_changes(names=[cst.ImportAlias(name=prefixed_module)])

        return updated_node


class CorePackageImportTransformer(cst.CSTTransformer):
    def __init__(self, core_module_names: set[str]) -> None:
        self.core_module_names: set[str] = core_module_names

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` statements for manager modules.

        Returns:
            The updated `ImportFrom` node with manager modules transformed to relative imports.

        """
        if original_node.relative or original_node.module is None:
            return updated_node

        full_module_name: str | None = get_full_name_for_node(original_node.module)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in self.core_module_names:
            prefixed_module = _create_prefixed_module(full_module_name, CORE_PREFIX)
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
        full_module_name: str | None = get_full_name_for_node(original_node.names[0].name)
        if not full_module_name:
            return updated_node

        first_module_part: str = full_module_name.split(".", maxsplit=1)[0]

        if first_module_part in self.core_module_names:
            return cst.ImportFrom(
                module=cst.Name(value="core"),
                names=[cst.ImportAlias(name=cst.Name(value=first_module_part))],
                relative=(cst.Dot(), cst.Dot()),
            )

        return updated_node


class CorePackageInternalImportTransformer(cst.CSTTransformer):
    def __init__(self, core_module_names: set[str], current_module_name: str) -> None:
        self.core_module_names: set[str] = core_module_names
        self.current_module_name: str = current_module_name

    def leave_ImportFrom(  # noqa: N802
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform `from <module> import ...` to `from .<module> import ...` for core modules.

        Returns:
            The updated `ImportFrom` node with a relative import.

        """
        if original_node.relative or original_node.module is None:
            return updated_node

        full_module_name: str | None = get_full_name_for_node(original_node.module)
        if not full_module_name:
            return updated_node

        # Check if the imported module is a core module and not the current module
        if (
            full_module_name in self.core_module_names
            and full_module_name != self.current_module_name
        ):
            return updated_node.with_changes(relative=(cst.Dot(),))

        return updated_node

    def leave_Import(  # noqa: N802
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.ImportFrom | cst.Import:
        """Transform `import <module>` to `from . import <module>` for core modules.

        Returns:
            The updated `Import` or a new `ImportFrom` node for manager modules.

        """
        if len(original_node.names) != 1:
            # Assuming one module per import, as per ruff formatting.
            return updated_node

        full_module_name: str | None = get_full_name_for_node(original_node.names[0].name)
        if not full_module_name:
            return updated_node

        if (
            full_module_name in self.core_module_names
            and full_module_name != self.current_module_name
        ):
            return cst.ImportFrom(
                module=None,
                names=[cst.ImportAlias(name=cst.Name(value=full_module_name))],
                relative=(cst.Dot(),),
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
