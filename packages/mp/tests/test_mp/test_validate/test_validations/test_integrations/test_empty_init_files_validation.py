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

"""Tests for the EmptyInitFilesValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from mp.core.exceptions import NonFatalValidationError
from mp.validate.validations.integrations.empty_init_files_validation import (
    EmptyInitFilesValidation,
)

if TYPE_CHECKING:
    import pathlib


class TestEmptyInitFilesValidation:
    """Test suite for the EmptyInitFilesValidation runner."""

    validator_runner = EmptyInitFilesValidation()

    def test_success_on_empty_init_file(self, temp_integration: pathlib.Path) -> None:
        """Test that a completely empty __init__.py passes validation."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("", encoding="utf-8")

        self.validator_runner.run(temp_integration)

    def test_success_on_license_header_only(self, temp_integration: pathlib.Path) -> None:
        """Test that __init__.py with only a license header comment passes."""
        license_header = (
            "# Copyright 2026 Google LLC\n"
            "#\n"
            '# Licensed under the Apache License, Version 2.0 (the "License");\n'
            "# you may not use this file except in compliance with the License.\n"
            "# You may obtain a copy of the License at\n"
            "#\n"
            "#     http://www.apache.org/licenses/LICENSE-2.0\n"
            "#\n"
            "# Unless required by applicable law or agreed to in writing, software\n"
            '# distributed under the License is distributed on an "AS IS" BASIS,\n'
            "# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n"
            "# See the License for the specific language governing permissions and\n"
            "# limitations under the License.\n"
        )
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text(license_header, encoding="utf-8")

        self.validator_runner.run(temp_integration)

    def test_success_on_future_import_only(self, temp_integration: pathlib.Path) -> None:
        """Test that __init__.py with only a future import passes."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("from __future__ import annotations\n", encoding="utf-8")

        self.validator_runner.run(temp_integration)

    def test_failure_on_init_with_real_import(self, temp_integration: pathlib.Path) -> None:
        """Test that __init__.py with a real import statement fails."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("import os\n", encoding="utf-8")

        with pytest.raises(NonFatalValidationError, match=r"__init__\.py files must be empty"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_init_with_from_import(self, temp_integration: pathlib.Path) -> None:
        """Test that __init__.py with a from-import (not future) statement fails."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("from .some_module import SomeClass\n", encoding="utf-8")

        with pytest.raises(NonFatalValidationError, match=r"__init__\.py files must be empty"):
            self.validator_runner.run(temp_integration)

    def test_tests_dir_init_not_checked(self, temp_integration: pathlib.Path) -> None:
        """Test that __init__.py inside the tests/ directory is not validated."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        tests_init = tests_dir / "__init__.py"
        tests_init.write_text("import os\nfrom something import bad\n", encoding="utf-8")

        # Should not raise — tests/ is not in _CHECKED_DIRS
        self.validator_runner.run(temp_integration)

    def test_missing_init_file_in_checked_dir_is_skipped(self, temp_integration: pathlib.Path) -> None:
        """Test that a missing __init__.py in a checked dir is skipped gracefully."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.unlink(missing_ok=True)

        # Should not raise — missing file is simply skipped
        self.validator_runner.run(temp_integration)

    def test_ci_context_with_no_changes_skips(self, temp_integration: pathlib.Path) -> None:
        """Test that in CI with no changed files the validation is skipped."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("import os\n", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[],
            ),
        ):
            # No changes reported — validation is skipped, no error raised
            self.validator_runner.run(temp_integration)

    def test_ci_context_with_changes_validates(self, temp_integration: pathlib.Path) -> None:
        """Test that in CI with changed files the validation runs and can fail."""
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("import os\n", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[init_file],
            ),
            pytest.raises(NonFatalValidationError, match=r"__init__\.py files must be empty"),
        ):
            self.validator_runner.run(temp_integration)

    def test_non_init_change_still_validates_all_inits(self, temp_integration: pathlib.Path) -> None:
        """The CI gate is integration-level (any change triggers), not file-level.

        Changing a non-init file (e.g. an action) still causes ALL __init__.py
        files in checked dirs to be validated.
        """
        init_file = temp_integration / "actions" / "__init__.py"
        init_file.write_text("import os\n", encoding="utf-8")  # bad content
        other_changed = temp_integration / "actions" / "ping.py"  # different file changed

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[other_changed],
            ),
            # Integration has changes → all inits validated → bad actions/__init__.py caught
            pytest.raises(NonFatalValidationError, match=r"__init__\.py files must be empty"),
        ):
            self.validator_runner.run(temp_integration)
