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

# type: ignore  # noqa: PGH003

from __future__ import annotations

import unittest.mock
from typing import TYPE_CHECKING

import pytest

import mp.core.unix
from mp.core.constants import RELEASE_NOTES_FILE
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.playbooks.version_bump_validation import (
    _create_data_for_version_bump_validation,  # noqa: PLC2701
    _version_bump_validation_run_checks,  # noqa: PLC2701
)

if TYPE_CHECKING:
    from pathlib import Path

OLD_RN_CONTENT = """
-   deprecated: true
    description: New Playbook Added - Mock Playbook.
    integration_version: 1.0
    item_name: Playbook Name
    item_type: Playbook
    new: true
    regressive: false
    removed: false
    ticket_number: some ticket"""

RN_ENTRY_TEMPLATE = """
-   deprecated: true
    description: New Playbook Added - Mock Playbook.
    integration_version: {version}
    item_name: Playbook Name
    item_type: Playbook
    new: true
    regressive: true
    removed: false
    ticket_number: ticket"""


def _setup_test_files(
    temp_playbook: Path,
    new_rn_content: str,
) -> Path:
    """Write content to mock playbook files and return their paths."""
    rn_path = temp_playbook / RELEASE_NOTES_FILE
    rn_path.write_text(new_rn_content, encoding="utf-8")
    return rn_path


class TestVersionBumpValidationFlow:
    def test_version_bump_valid(self, temp_non_built_playbook: Path) -> None:
        new_rn_entry = RN_ENTRY_TEMPLATE.format(version="2.0")
        new_rn_content = OLD_RN_CONTENT + new_rn_entry
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.return_value = OLD_RN_CONTENT
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            assert existing_files["rn"]["old"].version == 1.0
            assert existing_files["rn"]["new"][0].version == 2.0

            _version_bump_validation_run_checks(existing_files, new_files)

    def test_version_bump_invalid_increment_fail(self, temp_non_built_playbook: Path) -> None:
        new_rn_entry = RN_ENTRY_TEMPLATE.format(version="3.0")
        new_rn_content = OLD_RN_CONTENT + new_rn_entry
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.return_value = OLD_RN_CONTENT
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            assert existing_files["rn"]["old"].version == 1.0
            assert existing_files["rn"]["new"][0].version == 3.0

            with pytest.raises(NonFatalValidationError) as error_msg:
                _version_bump_validation_run_checks(existing_files, new_files)

            assert (
                "The release note's version must be incremented to 2.0 and "
                "be consistent in all the newly added notes." in str(error_msg.value)
            )

    def test_version_bump_float_fail(
        self,
        temp_non_built_playbook: Path,
    ) -> None:
        new_rn_entry = RN_ENTRY_TEMPLATE.format(version="1.5")
        new_rn_content = OLD_RN_CONTENT + new_rn_entry
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.return_value = OLD_RN_CONTENT
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            assert existing_files["rn"]["old"].version == 1.0
            assert existing_files["rn"]["new"][0].version == 1.5

            with pytest.raises(NonFatalValidationError, match=r"must be incremented to 2.0"):
                _version_bump_validation_run_checks(existing_files, new_files)

    def test_valid_new_playbook_valid(self, temp_non_built_playbook: Path) -> None:
        new_rn_content = RN_ENTRY_TEMPLATE.format(version="1.0")
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.side_effect = mp.core.unix.NonFatalCommandError(
                "File not found on main branch"
            )
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            assert not existing_files["rn"].get("old")
            assert len(new_files["rn"]) == 1
            assert new_files["rn"][0].version == 1.0

            _version_bump_validation_run_checks(existing_files, new_files)

    def test_new_playbook_wrong_version_fail(self, temp_non_built_playbook: Path) -> None:
        new_rn_content = RN_ENTRY_TEMPLATE.format(version="2.0")
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.side_effect = mp.core.unix.NonFatalCommandError(
                "File not found on main branch"
            )
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            assert new_files["rn"][0].version == 2.0

            with pytest.raises(NonFatalValidationError, match=r"must be initialize to 1\.0"):
                _version_bump_validation_run_checks(existing_files, new_files)

    def test_playbook_with_multiple_new_release_notes_version_bump_valid(
        self,
        temp_non_built_playbook: Path,
    ) -> None:
        rn_entry_a = RN_ENTRY_TEMPLATE.format(version="2.0")
        rn_entry_b = RN_ENTRY_TEMPLATE.format(version="2.0")
        new_rn_content = OLD_RN_CONTENT + rn_entry_a + rn_entry_b
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.return_value = OLD_RN_CONTENT
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            new_notes = existing_files["rn"]["new"]
            assert new_notes is not None
            assert len(new_notes) == 2
            assert all(note.version == 2.0 for note in new_notes)

            _version_bump_validation_run_checks(existing_files, new_files)

    def test_playbook_with_multiple_invalid_new_release_notes_versions_fail(
        self,
        temp_non_built_playbook: Path,
    ) -> None:
        rn_entry_a = RN_ENTRY_TEMPLATE.format(version="2.0")
        rn_entry_b = RN_ENTRY_TEMPLATE.format(version="4.0")
        new_rn_content = OLD_RN_CONTENT + rn_entry_a + rn_entry_b
        rn_path = _setup_test_files(temp_non_built_playbook, new_rn_content)

        with unittest.mock.patch("mp.core.unix.get_file_content_from_main_branch") as mock_git:
            mock_git.return_value = OLD_RN_CONTENT
            existing_files, new_files = _create_data_for_version_bump_validation(rn_path)

            new_notes = existing_files["rn"]["new"]
            assert new_notes is not None
            assert len(new_notes) == 2

            with pytest.raises(NonFatalValidationError, match=r"The release note's version must "):
                _version_bump_validation_run_checks(existing_files, new_files)
