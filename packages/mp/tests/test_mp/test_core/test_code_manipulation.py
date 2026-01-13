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

    # Test `import <sdk_module>, <sdk_module2>`
    import_content = f"import {sdk_module}, Siemplify"
    expected_import_content = f"import {SDK_PREFIX}{sdk_module}, {SDK_PREFIX}Siemplify"
    transformed_import_content = apply_transformers(import_content, [transformer])
    assert transformed_import_content == expected_import_content

    # Test `import <sdk_module> as alias`
    import_as_content = f"import {sdk_module} as sm"
    expected_import_as_content = f"import {SDK_PREFIX}{sdk_module} as sm"
    transformed_import_as_content = apply_transformers(import_as_content, [transformer])
    assert transformed_import_as_content == expected_import_as_content

    # Test `from <sdk_module> import something`
    from_import_content = f"from {sdk_module} import a, b"
    expected_from_import_content = f"from {SDK_PACKAGE_NAME}.{sdk_module} import a, b"
    transformed_from_import_content = apply_transformers(from_import_content, [transformer])
    assert transformed_from_import_content == expected_from_import_content

    # Test `from <sdk_module> import something as s`
    from_import_as_content = f"from {sdk_module} import something as s"
    expected_from_import_as_content = f"from {SDK_PACKAGE_NAME}.{sdk_module} import something as s"
    transformed_from_import_as_content = apply_transformers(from_import_as_content, [transformer])
    assert transformed_from_import_as_content == expected_from_import_as_content

    # Test `import <sdk_module>.submodule as alias`
    import_content = f"import {sdk_module}.submodule as alias"
    expected_import_content = f"import {SDK_PREFIX}{sdk_module}.submodule as alias"
    transformed_import_content = apply_transformers(import_content, [transformer])
    assert transformed_import_content == expected_import_content

    # Test `import <sdk_module>.submodule as alias, <sdk_module>.submodule2 as alias2`
    import_content = f"import {sdk_module}.submodule as alias, {sdk_module}.submodule2 as alias2"
    expected_import_content = (
        f"import {SDK_PREFIX}{sdk_module}.submodule as alias, "
        f"{SDK_PREFIX}{sdk_module}.submodule2 as alias2"
    )
    transformed_import_content = apply_transformers(import_content, [transformer])
    assert transformed_import_content == expected_import_content

    # Test `import <sdk_module>.submodule as alias, non-sdk_module.submodule2 as alias2`
    import_content = f"import {sdk_module}.submodule as alias, another_module.submodule2 as alias2"
    expected_import_content = (
        f"import {SDK_PREFIX}{sdk_module}.submodule as alias, another_module.submodule2 as alias2"
    )
    transformed_import_content = apply_transformers(import_content, [transformer])
    assert transformed_import_content == expected_import_content


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
        ("manager_import_as", "import manager as m", "from ..core import manager as m"),
        (
            "manager_from_import",
            "from manager import some_func",
            f"from ..{CORE_PREFIX}manager import some_func",
        ),
        (
            "manager_from_import_as",
            "from manager import some_func as sf",
            f"from ..{CORE_PREFIX}manager import some_func as sf",
        ),
        (
            "multiple_managers_import",
            "import manager1, manager2",
            "from ..core import manager1, manager2",
        ),
        (
            "manager_from_import_multiple",
            "from manager import a, b",
            f"from ..{CORE_PREFIX}manager import a, b",
        ),
        (
            "mixed_core_non_core_import",
            "import manager, requests",
            "import requests\nfrom ..core import manager",
        ),
    ],
)
def test_core_package_import_transformer(
    test_name: str, initial_content: str, expected_content: str
) -> None:
    """Verify that `CorePackageImportTransformer` correctly modifies file content."""
    transformer = CorePackageImportTransformer({"manager", "manager1", "manager2"})
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
        (
            "core_internal_import_as_alias",
            "import constants as const",
            "from . import constants as const",
        ),
        (
            "multiple_internal_imports",
            "import constants, manager",
            "from . import constants, manager",
        ),
        (
            "from_internal_import_multiple",
            "from constants import a, b",
            "from .constants import a, b",
        ),
        (
            "mixed_internal_non_core_import",
            "import constants, requests",
            "import requests\nfrom . import constants",
        ),
    ],
)
def test_core_package_internal_import_transformer(
    test_name: str, initial_content: str, expected_content: str
) -> None:
    """Verify that `CorePackageInternalImportTransformer` correctly modifies file content."""
    transformer = CorePackageInternalImportTransformer(
        {"constants", "api_client", "manager"}, "api_client"
    )
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


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content"),
    [
        # Reverse of SdkImportTransformer
        ("sdk_import", f"import {SDK_PREFIX}SiemplifyAction", "import SiemplifyAction"),
        (
            "sdk_import_multiple",
            f"import {SDK_PREFIX}Siemplify, {SDK_PREFIX}SiemplifyAction",
            "import Siemplify, SiemplifyAction",
        ),
        ("sdk_import_as", f"import {SDK_PREFIX}Siemplify as S", "import Siemplify as S"),
        (
            "sdk_from_import",
            f"from {SDK_PACKAGE_NAME}.SiemplifyUtils import output_handler",
            "from SiemplifyUtils import output_handler",
        ),
        (
            "sdk_from_import_as",
            f"from {SDK_PACKAGE_NAME}.SiemplifyUtils import output_handler as oh",
            "from SiemplifyUtils import output_handler as oh",
        ),
        ("sdk_import_submodule", f"import {SDK_PREFIX}Siemplify.sub", "import Siemplify.sub"),
        # Reverse of CorePackageImportTransformer
        ("core_package_import", "from ..core import manager", "import manager"),
        ("core_package_import_as", "from ..core import manager as m", "import manager as m"),
        (
            "core_package_from_import",
            f"from ..{CORE_PREFIX}manager import some_func",
            "from manager import some_func",
        ),
        (
            "core_package_from_import_as",
            f"from ..{CORE_PREFIX}manager import some_func as sf",
            "from manager import some_func as sf",
        ),
        (
            "core_package_multiple_imports",
            "from ..core import manager1, manager2",
            "import manager1, manager2",
        ),
        (
            "core_package_from_import_multiple",
            f"from ..{CORE_PREFIX}manager import a, b",
            "from manager import a, b",
        ),
        # Reverse of CorePackageInternalImportTransformer
        ("core_internal_import", "from . import constants", "import constants"),
        (
            "core_internal_from_import",
            "from .constants import MY_CONST",
            "from constants import MY_CONST",
        ),
        (
            "core_internal_import_as",
            "from . import constants as const",
            "import constants as const",
        ),
        (
            "core_internal_multiple_imports",
            "from . import constants, manager",
            "import constants, manager",
        ),
        (
            "core_internal_from_import_multiple",
            "from .constants import a, b",
            "from constants import a, b",
        ),
    ],
)
def test_import_transformer(test_name: str, initial_content: str, expected_content: str) -> None:
    """Verify that `ImportTransformer` correctly modifies file content."""
    transformed_content = restructure_script_imports(initial_content)
    assert transformed_content == expected_content
