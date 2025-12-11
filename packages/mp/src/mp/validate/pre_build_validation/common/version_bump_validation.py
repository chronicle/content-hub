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
from mp.core.constants import PROJECT_FILE, RELEASE_NOTES_FILE
from mp.core.data_models.pyproject_toml import PyProjectToml
from mp.core.data_models.release_notes.metadata import ReleaseNote
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


class TomlFileVersions(TypedDict):
    """Structure specifically for TOML file versions."""

    old: NotRequired[PyProjectToml | None]
    new: NotRequired[PyProjectToml | None]


class ReleaseNoteFileVersions(TypedDict):
    """Structure specifically for release note file versions."""

    old: NotRequired[ReleaseNote | None]
    new: NotRequired[list[ReleaseNote] | None]


class ExistingIntegrationFiles(TypedDict):
    """Structure for existing integration files with old and new versions."""

    toml: TomlFileVersions
    rn: ReleaseNoteFileVersions


class NewIntegrationFiles(TypedDict):
    """Structure for new integration files (only current versions)."""

    toml: NotRequired[PyProjectToml | None]
    rn: NotRequired[list[ReleaseNote] | None]


VersionBumpValidationData: TypeAlias = tuple[ExistingIntegrationFiles, NewIntegrationFiles]


@dataclasses.dataclass(slots=True, frozen=True)
class VersionBumpValidation:
    name: str = "Integration Version Bump"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Validate that `project.toml` and `release_notes.yml` files are correctly versioned.

        Args:
            integration_path (Path): Path to the integration directory.

        Raises:
            NonFatalValidationError: If versioning rules are violated.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if not head_sha:
            return

        changed_files: list[Path] = mp.core.unix.get_files_unmerged_to_main_branch(
            "main", head_sha, integration_path
        )

        if not changed_files:
            return

        rn_path: Path | None = None
        toml_path: Path | None = None
        for p in changed_files:
            if p.name == PROJECT_FILE:
                toml_path = p
            elif p.name == RELEASE_NOTES_FILE:
                rn_path = p

        msg: str
        if not rn_path and not toml_path:
            msg = "project.toml and release_notes.yml files must be updated before PR"
            raise NonFatalValidationError(msg)

        if not toml_path:
            msg = "project.toml file must be updated before PR"
            raise NonFatalValidationError(msg)

        if not rn_path:
            msg = "release_notes.yml file must be updated before PR"
            raise NonFatalValidationError(msg)

        existing_files, new_files = _create_data_for_version_bump_validation(rn_path, toml_path)
        _version_bump_validation_run_checks(existing_files, new_files)


def _create_data_for_version_bump_validation(
    rn_path: Path,
    toml_path: Path,
) -> VersionBumpValidationData:
    existing_files: ExistingIntegrationFiles = {
        "toml": TomlFileVersions(),
        "rn": ReleaseNoteFileVersions(),
    }
    new_files: NewIntegrationFiles = NewIntegrationFiles()

    try:
        old_toml_content = mp.core.unix.get_file_content_from_main_branch(toml_path)
        existing_files["toml"]["old"] = PyProjectToml.from_toml_str(old_toml_content)
        existing_files["toml"]["new"] = PyProjectToml.from_toml_str(
            toml_path.read_text(encoding="utf-8")
        )

        old_rn_content = mp.core.unix.get_file_content_from_main_branch(rn_path)
        existing_files["rn"]["old"] = _get_last_note(old_rn_content)
        existing_files["rn"]["new"] = _get_new_rn_notes(
            rn_path.read_text(encoding="utf-8"), old_rn_content
        )

    except mp.core.unix.NonFatalCommandError:
        new_files["toml"] = PyProjectToml.from_toml_str(toml_path.read_text(encoding="utf-8"))
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
    existing_files: ExistingIntegrationFiles,
    new_files: NewIntegrationFiles,
) -> None:
    msg: str
    if (new_toml := existing_files["toml"].get("new")) and (
        old_toml := existing_files["toml"].get("old")
    ):
        toml_new_version: float = new_toml.project.version
        toml_old_version: float = old_toml.project.version

        if toml_new_version != toml_old_version + 1.0:
            msg = "The project.toml Version must be incremented by exactly 1.0."
            raise NonFatalValidationError(msg)

        new_notes: list[ReleaseNote] | None = existing_files["rn"].get("new")
        if not _rn_is_valid(new_notes, toml_new_version):
            msg = (
                "The release note's version must match the new version of the project.toml and be"
                " consistent in all the newly added notes."
            )
            raise NonFatalValidationError(msg)

    elif (new_toml := new_files["toml"]) and (new_notes := new_files["rn"]):
        toml_version: float = new_toml.project.version
        if toml_version != 1.0 or not _rn_is_valid(new_notes):
            msg = (
                "New integration project.toml and release_note.yaml version must be initialize to"
                " 1.0"
            )
            raise NonFatalValidationError(msg)

    else:
        msg = "New integration missing project.toml and/or release_note.yaml."
        raise NonFatalValidationError(msg)


def _rn_is_valid(new_notes: list[ReleaseNote] | None, version_to_compare: float = 1.0) -> bool:
    return new_notes is not None and all(
        new_note.version == version_to_compare for new_note in new_notes
    )
