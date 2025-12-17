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

from typing import TYPE_CHECKING

import pytest

from mp.core.code_manipulation import (
    CORE_PREFIX,
    SDK_PREFIX,
    CorePackageImportTransformer,
    CorePackageInternalImportTransformer,
    FutureAnnotationsTransformer,
    SdkImportTransformer,
    apply_transformers,
    restructure_script_imports,
)
from mp.core.constants import (
    COMMON_SCRIPTS_DIR,
    CORE_SCRIPTS_DIR,
    SDK_MODULES,
    SDK_PACKAGE_NAME,
)

if TYPE_CHECKING:
    import libcst


@pytest.mark.parametrize(
    ("original_import", "expected_restructured_import"),
    [
        (
            f"from ..{CORE_SCRIPTS_DIR}.module import something as s",
            "from module import something as s",
        ),
        (
            f"from ..{CORE_SCRIPTS_DIR} import another_thing, yet_another as y",
            "import another_thing, yet_another as y",
        ),
        (
            f"from {CORE_SCRIPTS_DIR} import another_thing, yet_another as y",
            "import another_thing, yet_another as y",
        ),
        (
            f"from ...{COMMON_SCRIPTS_DIR}.module.sub.a.b.c.d.e import something as s",
            "from e import something as s",
        ),
        (
            f"from ...{COMMON_SCRIPTS_DIR} import another_thing as at, yet_another",
            "import another_thing as at, yet_another",
        ),
        (
            f"from {COMMON_SCRIPTS_DIR} import another_thing as at, yet_another",
            "import another_thing as at, yet_another",
        ),
        (
            f"from ...{SDK_PACKAGE_NAME}.module.sub.a.b.c.d.e import something as s",
            "from e import something as s",
        ),
        (
            f"from ...{SDK_PACKAGE_NAME} import another_thing as at, yet_another",
            "import another_thing as at, yet_another",
        ),
        (
            f"from {SDK_PACKAGE_NAME} import another_thing as at, yet_another",
            "import another_thing as at, yet_another",
        ),
        (
            "from . import utils, constants as c",
            "import utils, constants as c",
        ),
        (
            "from .. import utils, constants as c",
            "import utils, constants as c",
        ),
        (
            "from .data_models import Integration as I",
            "from data_models import Integration as I",
        ),
        (
            "from .......data_models import Integration as I",
            "from data_models import Integration as I",
        ),
        (
            f"from .{CORE_SCRIPTS_DIR}.{COMMON_SCRIPTS_DIR} import authentication as a",
            f"from {COMMON_SCRIPTS_DIR} import authentication as a",
        ),
        (
            f"from .{CORE_SCRIPTS_DIR}.{COMMON_SCRIPTS_DIR}.module import authentication as a",
            "from module import authentication as a",
        ),
        (
            f"from .{COMMON_SCRIPTS_DIR}.something import authentication as a",
            "from something import authentication as a",
        ),
        (
            f"from .{COMMON_SCRIPTS_DIR}.{CORE_SCRIPTS_DIR} import authentication as a",
            f"from {CORE_SCRIPTS_DIR} import authentication as a",
        ),
        (
            f"from .{COMMON_SCRIPTS_DIR}.{CORE_SCRIPTS_DIR}.module import authentication as a",
            "from module import authentication as a",
        ),
        (
            "from ..another_module import another_thing",
            "from another_module import another_thing",
        ),
        (
            "from ..another_package.sub_package.module import another_thing",
            "from another_package.sub_package.module import another_thing",
        ),
        ("import os", "import os"),
        ("import pathlib.Path", "import pathlib.Path"),
    ],
)
def test_other_imports_are_not_modified(
    original_import: str,
    expected_restructured_import: str,
) -> None:
    modified_code: str = restructure_script_imports(
        original_import,
    )
    assert modified_code == expected_restructured_import
    compile(modified_code, filename="test_import_errors", mode="exec")


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content"),
    [
        (
            "simple_import",
            "import SiemplifyAction",
            "from __future__ import annotations\nimport SiemplifyAction",
        ),
        (
            "with_double_quotes_docstring",
            '"""This is a module docstring."""\nimport SiemplifyAction',
            (
                '"""This is a module docstring."""\n'
                "from __future__ import annotations\n"
                "import SiemplifyAction"
            ),
        ),
        (
            "with_single_quotes_docstring",
            "'''This is a module docstring.'''\nimport SiemplifyAction",
            (
                "'''This is a module docstring.'''\n"
                "from __future__ import annotations\n"
                "import SiemplifyAction"
            ),
        ),
        (
            "with_single_quotes",
            "'This is a module docstring.'\nimport SiemplifyAction",
            (
                "'This is a module docstring.'\n"
                "from __future__ import annotations\n"
                "import SiemplifyAction"
            ),
        ),
        (
            "with_comment",
            "# This is a comment\nimport SiemplifyAction",
            "# This is a comment\nfrom __future__ import annotations\nimport SiemplifyAction",
        ),
        (
            "already_exists",
            "from __future__ import annotations\nimport SiemplifyAction",
            "from __future__ import annotations\nimport SiemplifyAction",
        ),
        ("empty_file", "", ""),
    ],
)
def test_future_annotations_transformer(
    test_name: str, initial_content: str, expected_content: str
) -> None:
    """Verify that `FutureAnnotationsTransformer` correctly modifies file content."""
    transformer = FutureAnnotationsTransformer()
    transformed_content = apply_transformers(initial_content, [transformer])
    assert transformed_content == expected_content


@pytest.mark.parametrize(
    "sdk_module",
    sorted(SDK_MODULES),
)
def test_sdk_import_transformer(sdk_module: str) -> None:
    """Verify that `SdkImportTransformer` correctly modifies file content."""
    transformer = SdkImportTransformer()

    # Test `import <sdk_module>`
    import_content = f"import {sdk_module}"
    expected_import_content = f"import {SDK_PREFIX}{sdk_module}"
    transformed_import_content = apply_transformers(import_content, [transformer])
    assert transformed_import_content == expected_import_content

    # Test `from <sdk_module> import something`
    from_import_content = f"from {sdk_module} import something"
    expected_from_import_content = f"from {SDK_PACKAGE_NAME}.{sdk_module} import something"
    transformed_from_import_content = apply_transformers(from_import_content, [transformer])
    assert transformed_from_import_content == expected_from_import_content


def test_sdk_import_transformer_unrelated_import() -> None:
    """Verify that `SdkImportTransformer` doesn't modify unrelated imports."""
    transformer = SdkImportTransformer()
    unrelated_import = "import other_module"
    transformed_content = apply_transformers(unrelated_import, [transformer])
    assert transformed_content == unrelated_import


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content"),
    [
        ("manager_import", "import manager", "from ..core import manager"),
        (
            "manager_from_import",
            "from manager import some_func",
            f"from ..{CORE_PREFIX}manager import some_func",
        ),
    ],
)
def test_core_package_import_transformer(
    test_name: str, initial_content: str, expected_content: str
) -> None:
    """Verify that `CorePackageImportTransformer` correctly modifies file content."""
    transformer = CorePackageImportTransformer({"manager"})
    transformed_content = apply_transformers(initial_content, [transformer])
    assert transformed_content == expected_content


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content"),
    [
        ("core_internal_import", "import constants", "from . import constants"),
        (
            "core_internal_from_import",
            "from constants import MY_CONST",
            "from .constants import MY_CONST",
        ),
        ("import_self", "import api_client", "import api_client"),
    ],
)
def test_core_package_internal_import_transformer(
    test_name: str, initial_content: str, expected_content: str
) -> None:
    """Verify that `CorePackageInternalImportTransformer` correctly modifies file content."""
    transformer = CorePackageInternalImportTransformer({"constants", "api_client"}, "api_client")
    transformed_content = apply_transformers(initial_content, [transformer])
    assert transformed_content == expected_content


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content", "transformers"),
    [
        (
            "sdk_and_manager_imports",
            "import manager\nimport SiemplifyAction",
            (
                "from __future__ import annotations\n"
                "from ..core import manager\n"
                "import soar_sdk.SiemplifyAction"
            ),
            [
                FutureAnnotationsTransformer(),
                SdkImportTransformer(),
                CorePackageImportTransformer({"manager"}),
            ],
        ),
        (
            "all_transformers",
            "import constants\nfrom SiemplifyUtils import output_handler",
            (
                "from __future__ import annotations\n"
                "from . import constants\n"
                "from soar_sdk.SiemplifyUtils import output_handler"
            ),
            [
                FutureAnnotationsTransformer(),
                SdkImportTransformer(),
                CorePackageInternalImportTransformer({"constants", "api_client"}, "api_client"),
            ],
        ),
    ],
)
def test_mixed_transformers(
    test_name: str,
    initial_content: str,
    expected_content: str,
    transformers: list[libcst.CSTTransformer],
) -> None:
    """Verify that `apply_transformers` correctly modifies file content
    with multiple transformers."""
    transformed_content = apply_transformers(initial_content, transformers)
    assert transformed_content == expected_content
