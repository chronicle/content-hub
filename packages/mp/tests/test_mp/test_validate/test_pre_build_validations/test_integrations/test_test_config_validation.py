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

"""Tests for the TestConfigValidation class."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.test_config_validation import (
    TestConfigValidation,
)

if TYPE_CHECKING:
    import pathlib


class TestTestConfigValidation:
    """Test suite for the TestConfigValidation runner."""

    validator_runner = TestConfigValidation()

    def test_success_on_valid_config(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid tests/config.json (dict) passes validation."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        config_file = tests_dir / "config.json"
        config_file.write_text(json.dumps({"api_root": "https://example.com", "api_key": "secret"}), encoding="utf-8")

        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_config(self, temp_integration: pathlib.Path) -> None:
        """Test failure when tests/config.json is absent."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        # Ensure config.json does not exist
        config_file = tests_dir / "config.json"
        config_file.unlink(missing_ok=True)

        with pytest.raises(NonFatalValidationError, match=r"missing tests/config\.json"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_invalid_json(self, temp_integration: pathlib.Path) -> None:
        """Test failure when tests/config.json contains malformed JSON."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        config_file = tests_dir / "config.json"
        config_file.write_text("{ this is not valid json }", encoding="utf-8")

        with pytest.raises(NonFatalValidationError, match="not valid JSON"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_list_config(self, temp_integration: pathlib.Path) -> None:
        """Test failure when tests/config.json is a JSON array instead of an object."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        config_file = tests_dir / "config.json"
        config_file.write_text(json.dumps([{"api_root": "https://example.com"}]), encoding="utf-8")

        with pytest.raises(NonFatalValidationError, match="must be a JSON object"):
            self.validator_runner.run(temp_integration)

    def test_no_tests_directory_is_skipped_gracefully(self, temp_integration: pathlib.Path) -> None:
        """Test that a missing tests/ directory is skipped without raising."""
        tests_dir = temp_integration / "tests"
        # Remove the tests directory entirely if it exists
        if tests_dir.exists():
            shutil.rmtree(tests_dir)

        # Should not raise — no tests dir is handled gracefully
        self.validator_runner.run(temp_integration)

    def test_ci_context_with_no_changes_skips(self, temp_integration: pathlib.Path) -> None:
        """Test that in CI with no changed files the validation is skipped."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        # Deliberately omit config.json — would normally fail

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[],
            ),
        ):
            # No changed files reported — validation is skipped entirely
            self.validator_runner.run(temp_integration)

    def test_ci_context_with_changes_validates(self, temp_integration: pathlib.Path) -> None:
        """Test that in CI with changed files the validation runs and can fail."""
        tests_dir = temp_integration / "tests"
        tests_dir.mkdir(exist_ok=True)
        # Deliberately omit config.json — should fail once CI gate is open
        config_file = tests_dir / "config.json"
        config_file.unlink(missing_ok=True)

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[temp_integration / "actions" / "ping.py"],
            ), pytest.raises(NonFatalValidationError, match=r"missing tests/config\.json")
        ):
            self.validator_runner.run(temp_integration)
