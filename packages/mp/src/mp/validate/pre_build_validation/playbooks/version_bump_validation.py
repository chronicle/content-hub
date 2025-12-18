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

import dataclasses
import os
from typing import TYPE_CHECKING, NotRequired, TypeAlias, TypedDict

import mp.core.unix
from mp.core.constants import RELEASE_NOTES_FILE
from mp.core.data_models.common.release_notes.metadata import ReleaseNote
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


class ReleaseNoteFileVersions(TypedDict):
    """Structure specifically for release note file versions."""

    old: NotRequired[ReleaseNote | None]
    new: NotRequired[list[ReleaseNote] | None]


class ExistingPlaybookFiles(TypedDict):
    """Structure for existing playbook files with old and new versions."""

    rn: ReleaseNoteFileVersions


class NewPlaybookFiles(TypedDict):
    """Structure for new playbook files (only current versions)."""

    rn: NotRequired[list[ReleaseNote] | None]


VersionBumpValidationData: TypeAlias = tuple[ExistingPlaybookFiles, NewPlaybookFiles]


@dataclasses.dataclass(slots=True, frozen=True)
class VersionBumpValidation:
    name: str = "Playbook Version Bump"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate that `release_notes.yml` files are correctly versioned.

        Args:
            playbook_path (Path): Path to the playbook directory.

        Raises:
            NonFatalValidationError: If versioning rules are violated.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if not head_sha:
            return

        changed_files: list[Path] = mp.core.unix.get_files_unmerged_to_main_branch(
            "main", head_sha, playbook_path
        )

        if not changed_files:
            return

        rn_path: Path | None = None
        for p in changed_files:
            if p.name == RELEASE_NOTES_FILE:
                rn_path = p
                break

        if rn_path is None:
            msg = "release_notes.yml file must be updated before PR"
            raise NonFatalValidationError(msg)

        existing_files, new_files = _create_data_for_version_bump_validation(rn_path)
        _version_bump_validation_run_checks(existing_files, new_files)


def _create_data_for_version_bump_validation(
    rn_path: Path,
) -> VersionBumpValidationData:
    existing_files: ExistingPlaybookFiles = {
        "rn": ReleaseNoteFileVersions(),
    }
    new_files: NewPlaybookFiles = NewPlaybookFiles()

    try:
        old_rn_content = mp.core.unix.get_file_content_from_main_branch(rn_path)
        existing_files["rn"]["old"] = _get_last_note(old_rn_content)
        existing_files["rn"]["new"] = _get_new_rn_notes(
            rn_path.read_text(encoding="utf-8"), old_rn_content
        )

    except mp.core.unix.NonFatalCommandError:
        new_files["rn"] = ReleaseNote.from_non_built_str(rn_path.read_text(encoding="utf-8"))

    return existing_files, new_files


def _get_last_note(content: str) -> ReleaseNote | None:
    notes: list[ReleaseNote] = ReleaseNote.from_non_built_str(content)
    return notes[-1] if notes else None


def _get_new_rn_notes(new_rn_content: str, old_rn_content: str) -> list[ReleaseNote]:
    new_notes: list[ReleaseNote] = ReleaseNote.from_non_built_str(new_rn_content)
    old_notes: list[ReleaseNote] = ReleaseNote.from_non_built_str(old_rn_content)
    return new_notes[len(old_notes) :]


def _version_bump_validation_run_checks(
    existing_files: ExistingPlaybookFiles,
    new_files: NewPlaybookFiles,
) -> None:
    msg: str
    if old_rn := existing_files["rn"].get("old"):
        new_version: float = old_rn.version + 1.0
        new_notes: list[ReleaseNote] | None = existing_files["rn"].get("new")

        if not _rn_is_valid(new_notes, new_version):
            msg = (
                f"The release note's version must be incremented to {new_version} and be"
                " consistent in all the newly added notes."
            )
            raise NonFatalValidationError(msg)

    elif new_notes := new_files.get("rn"):
        if not _rn_is_valid(new_notes):
            msg = "New playbook release_note.yaml version must be initialize to 1.0"
            raise NonFatalValidationError(msg)

    elif not new_files.get("rn"):
        msg = "New playbook release_note.yaml cannot be empty."
        raise NonFatalValidationError(msg)


def _rn_is_valid(new_notes: list[ReleaseNote] | None, version_to_compare: float = 1.0) -> bool:
    return new_notes is not None and all(
        new_note.version == version_to_compare for new_note in new_notes
    )
