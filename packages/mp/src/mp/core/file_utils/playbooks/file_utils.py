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

import json
from typing import TYPE_CHECKING, Any

import rich

import mp.core.constants
import mp.core.file_utils.common.utils

if TYPE_CHECKING:
    from pathlib import Path


def get_playbook_repository_base_path(playbooks_classification: str) -> Path:
    """Get all content-hub playbooks repository path.

    Args:
        playbooks_classification: the name of the repository.

    Returns:
         list of paths to playbook repository root dir.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        get_playbook_base_dir() / playbooks_classification
    )


def get_playbook_base_dir() -> Path:
    """Get the root folder for the playbooks' repository.

    Returns:
        the root folder for the playbooks' repository.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_content_dir()
        / mp.core.constants.PLAYBOOKS_DIR_NAME
    )


def get_playbook_out_dir() -> Path:
    """Get the output directory for built playbooks.

    Returns:
        The path to the output directory for built playbooks.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        get_playbook_out_base_dir() / mp.core.constants.PLAYBOOK_OUT_DIR_NAME
    )


def get_playbook_out_base_dir() -> Path:
    """Get the base output directory for built playbooks.

    Returns:
        The path to the base output directory for built playbooks.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_out_contents_dir()
        / mp.core.constants.PLAYBOOK_BASE_OUT_DIR_NAME
    )


def is_non_built_playbook(playbook_path: Path) -> bool:
    """Check whether a playbook is non-built.

    Returns:
        Whether the playbook is in a non-built format

    """
    if not playbook_path.is_dir():
        return False

    steps_dir: Path = playbook_path / mp.core.constants.STEPS_DIR
    widgets_dir: Path = playbook_path / mp.core.constants.WIDGETS_DIR
    def_file: Path = playbook_path / mp.core.constants.DEFINITION_FILE
    display_info: Path = playbook_path / mp.core.constants.DISPLAY_INFO_FILE_MAME
    overviews_file: Path = playbook_path / mp.core.constants.OVERVIEWS_FILE_NAME
    trigger_file: Path = playbook_path / mp.core.constants.TRIGGER_FILE_NAME

    return (
        steps_dir.exists()
        and widgets_dir.exists()
        and def_file.exists()
        and display_info.exists()
        and overviews_file.exists()
        and trigger_file.exists()
    )


def is_built_playbook(path: Path) -> bool:
    """Check whether a path is a built-playbook.

    Returns:
        Whether the provided path is a built-playbook.

    """
    if not path.exists() or path.is_dir() or path.suffix != ".json":
        return False

    try:
        with path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        if not mp.core.constants.PLAYBOOK_MUST_HAVE_KEYS.issubset(data.keys()):
            rich.print(
                f"[red]Playbook is invalid, File {path.name} is missing one or more required keys:"
                f" {mp.core.constants.PLAYBOOK_MUST_HAVE_KEYS - data.keys()}[/red]"
            )
            return False

    except json.JSONDecodeError:
        rich.print(f"[red]Playbook is invalid,File {path.name} is not a valid JSON file.[/red]")
        return False
    except OSError as e:
        rich.print(f"[red]Error reading file {path.name}: {e}[/red]")
        return False

    return True
