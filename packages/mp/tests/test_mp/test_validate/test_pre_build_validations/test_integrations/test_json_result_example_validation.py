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

from pathlib import Path
from unittest import mock

import pytest

from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.json_result_example_validation import (
    JsonResultExampleValidation,
)

VALIDATOR = JsonResultExampleValidation()


class TestJsonResultExampleValidationLocal:
    """Local mp validate runs (no GITHUB_PR_SHA) — all action files are checked."""

    def test_action_with_example_passes(self, temp_integration: Path) -> None:
        # mock_integration already has ping.py (no JSON result) and
        # ping_JsonResult_example.json — baseline should pass
        VALIDATOR.run(temp_integration)

    def test_action_with_json_result_missing_example_fails(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")

        with pytest.raises(NonFatalValidationError, match="get_data"):
            VALIDATOR.run(temp_integration)

    def test_action_with_example_present_passes(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")
        example = temp_integration / "resources" / "get_data_JsonResult_example.json"
        example.write_text('{"key": "value"}', encoding="utf-8")

        VALIDATOR.run(temp_integration)  # no error

    def test_action_with_json_result_in_comment_ignored(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("# result.add_result_json(data)\n", encoding="utf-8")

        VALIDATOR.run(temp_integration)  # comment-only — no error

    def test_private_action_file_skipped(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "_helpers.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")

        VALIDATOR.run(temp_integration)  # _ prefix — skipped, no error

    def test_no_actions_dir_passes(self, temp_integration: Path) -> None:
        import shutil
        shutil.rmtree(temp_integration / "actions")
        VALIDATOR.run(temp_integration)  # no error


class TestJsonResultExampleValidationCI:
    """CI runs (GITHUB_PR_SHA set) — only changed action files are checked."""

    def test_changed_action_missing_example_fails(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=[action]),
        ):
            with pytest.raises(NonFatalValidationError, match="get_data"):
                VALIDATOR.run(temp_integration)

    def test_unchanged_action_missing_example_passes(self, temp_integration: Path) -> None:
        """Pre-existing action without example should not be flagged if not in diff."""
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")
        # action is NOT in the changed files list
        other_changed = [temp_integration / "definition.yaml"]

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=other_changed),
        ):
            VALIDATOR.run(temp_integration)  # pre-existing gap — not flagged

    def test_no_changes_skips_entirely(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=[]),
        ):
            VALIDATOR.run(temp_integration)  # skipped entirely

    def test_changed_action_with_example_passes(self, temp_integration: Path) -> None:
        action = temp_integration / "actions" / "get_data.py"
        action.write_text("result.add_result_json(data)", encoding="utf-8")
        example = temp_integration / "resources" / "get_data_JsonResult_example.json"
        example.write_text('{"key": "value"}', encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=[action]),
        ):
            VALIDATOR.run(temp_integration)  # no error

    def test_new_action_in_pr_checked(self, temp_integration: Path) -> None:
        """Newly added action files in the PR are subject to the check."""
        action = temp_integration / "actions" / "new_action.py"
        action.write_text("self.json_results = results", encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=[action]),
        ):
            with pytest.raises(NonFatalValidationError, match="new_action"):
                VALIDATOR.run(temp_integration)
