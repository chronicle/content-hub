"""Tests for the code_utilities module."""

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

from mp.core.code_utilities import (
    CorePackageImportTransformer,
    CorePackageInternalImportTransformer,
    FutureAnnotationsTransformer,
    SdkImportTransformer,
    apply_transformers,
)

if TYPE_CHECKING:
    import libcst


@pytest.mark.parametrize(
    ("test_name", "initial_content", "expected_content", "transformers"),
    [
        (
            "sdk_import",
            "import SiemplifyAction",
            "from __future__ import annotations\nimport soar_sdk.SiemplifyAction",
            [FutureAnnotationsTransformer(), SdkImportTransformer()],
        ),
        (
            "sdk_from_import",
            "from SiemplifyUtils import output_handler",
            (
                "from __future__ import annotations\n"
                "from soar_sdk.SiemplifyUtils import output_handler"
            ),
            [FutureAnnotationsTransformer(), SdkImportTransformer()],
        ),
        (
            "manager_import",
            "import manager",
            "from __future__ import annotations\nfrom ..core import manager",
            [
                FutureAnnotationsTransformer(),
                CorePackageImportTransformer({"manager"}),
            ],
        ),
        (
            "manager_from_import",
            "from manager import some_func",
            "from __future__ import annotations\nfrom ..core.manager import some_func",
            [
                FutureAnnotationsTransformer(),
                CorePackageImportTransformer({"manager"}),
            ],
        ),
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
            "unrelated_import",
            "import other_module",
            "from __future__ import annotations\nimport other_module",
            [
                FutureAnnotationsTransformer(),
                SdkImportTransformer(),
                CorePackageImportTransformer(set()),
            ],
        ),
        (
            "no_imports",
            "print('hello world')",
            "from __future__ import annotations\nprint('hello world')",
            [FutureAnnotationsTransformer(), SdkImportTransformer()],
        ),
        (
            "empty_file",
            "",
            "",
            [
                FutureAnnotationsTransformer(),
                SdkImportTransformer(),
                CorePackageImportTransformer({"manager"}),
            ],
        ),
        (
            "future_annotations_already_exists",
            "from __future__ import annotations\nimport SiemplifyAction",
            "from __future__ import annotations\nimport soar_sdk.SiemplifyAction",
            [FutureAnnotationsTransformer(), SdkImportTransformer()],
        ),
        (
            "core_internal_import",
            "import constants",
            "from __future__ import annotations\nfrom . import constants",
            [
                FutureAnnotationsTransformer(),
                CorePackageInternalImportTransformer({"constants", "api_client"}, "api_client"),
            ],
        ),
        (
            "core_internal_from_import",
            "from constants import MY_CONST",
            "from __future__ import annotations\nfrom .constants import MY_CONST",
            [
                FutureAnnotationsTransformer(),
                CorePackageInternalImportTransformer({"constants", "api_client"}, "api_client"),
            ],
        ),
    ],
)
def test_apply_transformers(
    test_name: str,
    initial_content: str,
    expected_content: str,
    transformers: list[libcst.CSTTransformer],
) -> None:
    """Verify that `apply_transformers` correctly modifies file content."""
    transformed_content = apply_transformers(initial_content, transformers)
    assert transformed_content == expected_content
