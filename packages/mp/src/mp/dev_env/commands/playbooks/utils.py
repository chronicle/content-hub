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

import subprocess  # noqa: S404
import zipfile
from typing import TYPE_CHECKING

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.playbooks.meta.display_info import PlaybookType
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.utils.common.utils import to_snake_case

if TYPE_CHECKING:
    from pathlib import Path


def get_playbook_path_by_name(playbook: str, *, custom: bool = False) -> Path:
    """Find the source path for a given playbook.

    Args:
        playbook: The name of the playbook to find.
        custom: Whether to search in the custom repository.

    Returns:
        The path to the playbook's source directory.

    Raises:
        typer.Exit: If the integration directory is not found.

    """
    playbooks_root = mp.core.file_utils.create_or_get_playbooks_root_dir()

    if custom:
        source_path = playbooks_root / mp.core.constants.CUSTOM_REPO_NAME / playbook
        if source_path.exists():
            return source_path

    for repo, folders in mp.core.constants.PLAYBOOKS_DIRS_NAMES_DICT.items():
        for folder in folders:
            if repo == mp.core.constants.COMMERCIAL_REPO_NAME:
                candidate = playbooks_root / folder / playbook
            else:
                candidate = playbooks_root / repo / folder / playbook

            if candidate.exists():
                return candidate

    rich.print(f"[red]Could not find source playbook at {playbooks_root}/.../{playbook}[/red]")
    raise typer.Exit(1)


def get_blocks_by_id(ids_to_find: set[str], *, custom: bool = False) -> set[str]:  # noqa: C901
    """Find blocks paths for a list of block identifiers.

    Args:
        ids_to_find: A list of unique string identifiers for the blocks to find.
        custom: Whether to search in the custom repository.

    Returns:
        A list of Path objects pointing to the source directories of the found blocks.

    """
    playbooks_root = mp.core.file_utils.create_or_get_playbooks_root_dir()
    result: set[str] = set()

    if custom:
        pass

    for repo, folders in mp.core.constants.PLAYBOOKS_DIRS_NAMES_DICT.items():
        for folder in folders:
            if repo == mp.core.constants.COMMERCIAL_REPO_NAME:
                source_folder = playbooks_root / folder
            else:
                source_folder = playbooks_root / repo / folder

            if not source_folder.exists():
                continue

            for block_path in source_folder.iterdir():
                if block_path.is_dir():
                    meta = PlaybookMetadata.from_non_built_path(block_path)

                    if meta.type_ == PlaybookType.BLOCK and meta.identifier in ids_to_find:
                        result.add(block_path.name)
                        ids_to_find.remove(meta.identifier)

            if not ids_to_find:
                return result

    if ids_to_find:
        missing_str = ", ".join(ids_to_find)
        rich.print(f"[red]Could not find the following blocks: {missing_str}[/red]")

    return result


def build_playbook(playbook_name: str) -> None:
    """Invoke the build command for a single playbook.

    Args:
        playbook_name: The name of the playbook to build.

    Raises:
        typer.Exit: If the build fails.

    """
    command: list[str] = ["mp", "build", "-p", playbook_name, "--quiet"]
    result = subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        rich.print(f"[red]Build failed:\n{result.stderr}[/red]")
        raise typer.Exit(result.returncode)

    rich.print(f"Build output:\n{result.stdout}")


def find_built_playbook(playbook_name: str, *, custom: bool = False) -> Path:
    """Find the built playbook path.

    Args:
        playbook_name: The name of the playbook to find.
        custom: Whether to search in the custom repository.

    Returns:
        Path: The path to the built playbook path)

    Raises:
        typer.Exit: If the built playbook is not found.

    """
    root: Path = mp.core.file_utils.get_playbook_out_base_dir()
    if custom:
        pass

    built_playbook_name: str = f"{to_snake_case(playbook_name)}{mp.core.constants.JSON_SUFFIX}"
    built_playbook: Path = root / mp.core.constants.PLAYBOOK_OUT_DIR_NAME / built_playbook_name
    if built_playbook.exists():
        return built_playbook

    rich.print(f"[red]Built playbook '{playbook_name}' not found in {root}")
    raise typer.Exit(1)


def zip_built_playbook(playbook_name: str, built_paths: list[Path]) -> Path:
    """Zips multiple built playbook components into a single archive.

    Args:
        playbook_name: The name to use for the resulting zip file.
        built_paths: A list of Path objects representing the files to be included in the zip.

    Returns:
        Path: The path to the created zip file.

    Raises:
        ValueError: If built_paths is empty.

    """
    if not built_paths:
        msg: str = "The list of paths to zip cannot be empty."
        raise ValueError(msg)

    zip_path = built_paths[0].parent / f"{playbook_name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in built_paths:
            zf.write(path, arcname=path.name)

    return zip_path
