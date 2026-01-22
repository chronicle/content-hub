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

import base64
import shutil
import subprocess  # noqa: S404
import zipfile
from pathlib import Path
from typing import Any

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.playbooks.meta.display_info import PlaybookType
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.utils.common.utils import to_snake_case


def get_playbook_path_by_name(playbook: str) -> Path:
    """Find the source path for a given playbook.

    Args:
        playbook: The name of the playbook to find.

    Returns:
        The path to the playbook's source directory.

    Raises:
        typer.Exit: If the integration directory is not found.

    """
    playbooks_root = mp.core.file_utils.create_or_get_playbooks_root_dir()

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


def get_block_names_by_ids(ids_to_find: set[str]) -> set[str]:
    """Find non-built blocks names in the repo given a set of block identifiers.

    Args:
        ids_to_find: A set of unique string identifiers for the blocks to find.

    Returns:
        A set of directory names (strings) of the found blocks.

    """
    remaining_ids = ids_to_find.copy()
    playbooks_root = mp.core.file_utils.create_or_get_playbooks_root_dir()
    result: set[str] = set()

    for repo, folders in mp.core.constants.PLAYBOOKS_DIRS_NAMES_DICT.items():
        for folder in folders:
            if repo == mp.core.constants.COMMERCIAL_REPO_NAME:
                source_folder = playbooks_root / folder
            else:
                source_folder = playbooks_root / repo / folder

            if not source_folder.exists():
                continue

            for block_path in source_folder.iterdir():
                if not block_path.is_dir():
                    continue

                meta = PlaybookMetadata.from_non_built_path(block_path)

                if meta.type_ == PlaybookType.BLOCK and meta.identifier in remaining_ids:
                    result.add(block_path.name)
                    remaining_ids.remove(meta.identifier)

            if not remaining_ids:
                return result

    if remaining_ids:
        missing_str = ", ".join(remaining_ids)
        rich.print(f"[red]Could not find the following blocks: {missing_str}[/red]")

    return result


def build_playbook(playbooks_names: set[str]) -> None:
    """Run the build command for a List of playbooks names.

    Args:
        playbooks_names: Set of playbooks names to build.

    Raises:
        typer.Exit: If the build fails.

    """
    command: list[str] = ["mp", "build"]
    for name in playbooks_names:
        command.extend(["-p", name])
    command.extend(["--quiet"])

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


def get_built_playbook_path(playbook_name: str) -> Path:
    """Find the built playbook path.

    Args:
        playbook_name: The name of the playbook to find.

    Returns:
        Path: The path to the built playbook path)

    Raises:
        typer.Exit: If the built playbook is not found.

    """
    root: Path = mp.core.file_utils.get_playbook_out_base_dir()

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


def find_playbook_identifier(playbook_name: str, installed_playbook: list[dict[str, Any]]) -> str:
    """Find playbook identifier from given playbook name.

    Args:
        playbook_name: The name of the playbook to find identifier for.
        installed_playbook: The list of installed playbooks to search in.

    Returns:
        str: The identifier of the playbook if found, otherwise raises an exception.

    Raises:
        typer.Exit: If the playbook is not found in installed playbooks.

    """
    for playbook_meta in installed_playbook:
        if playbook_meta["name"] == playbook_name:
            return playbook_meta["identifier"]

    rich.print(
        f"[red]Playbook '{playbook_name}' not found in installed playbooks in SOAR platform."
    )
    raise typer.Exit(1)


def deconstruct_playbook(built_playbook: Path) -> Path:
    """Deconstructs a built playbook and restores the source to its original directory.

    Args:
        built_playbook (Path): Path to the built playbook file.

    Returns:
        Path: Path to the deconstructed playbook.

    Raises:
        typer.Exit: If the deconstruction subprocess fails.

    """
    original_parent_folder = built_playbook.parent

    community_folder: Path = (
        mp.core.file_utils.create_or_get_playbooks_root_dir()
        / mp.core.constants.THIRD_PARTY_REPO_NAME
        / mp.core.constants.COMMUNITY_DIR_NAME
    )
    community_folder.mkdir(parents=True, exist_ok=True)
    target_path_in_community = community_folder / built_playbook.name

    shutil.move(str(built_playbook), str(target_path_in_community))

    command: list[str] = ["mp", "build", "-p", built_playbook.name, "-d", "--quiet"]
    result = subprocess.run(  # noqa: S603
        command, capture_output=True, check=False, text=True
    )

    if result.returncode != 0:
        rich.print(f"[red]Deconstruct failed:\n{result.stderr}[/red]")
        raise typer.Exit(result.returncode)

    non_built_path: Path = _get_deconstructed_playbook_path(built_playbook.stem)
    final_destination = original_parent_folder / non_built_path.name

    if final_destination.exists():
        shutil.rmtree(final_destination)

    shutil.move(str(non_built_path), str(original_parent_folder))

    if target_path_in_community.exists():
        target_path_in_community.unlink()

    return original_parent_folder / non_built_path.name


def _get_deconstructed_playbook_path(playbook_name: str) -> Path:
    root: Path = mp.core.file_utils.get_playbook_out_base_dir()
    non_built_playbook: Path = root / mp.core.constants.PLAYBOOK_OUT_DIR_NAME / playbook_name

    if non_built_playbook.exists():
        return non_built_playbook

    rich.print(f"[red]Non-built playbook '{playbook_name}' not found in {root}")
    raise typer.Exit(1)


def unzip_playbooks(
    zip_path: Path, dest: Path, include_playbook: str = "", exclude_playbook: str = ""
) -> list[Path]:
    """Unzips JSON playbooks to a destination.

    Args:
        zip_path: The path to the source ZIP file.
        dest: The directory where the files should be extracted.
        include_playbook: The name of the playbook to include. If empty, all playbooks are included.
        exclude_playbook: The name of the playbook to exclude.

    Returns:
        A list of paths to the successfully extracted JSON files.

    """
    result: list[Path] = []
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for file_info in zip_ref.infolist():
            original_filename = Path(file_info.filename).stem
            if original_filename == exclude_playbook:
                continue

            if include_playbook in {"", original_filename}:
                new_filename: str = (
                    f"{to_snake_case(original_filename)}{mp.core.constants.JSON_SUFFIX}"
                )
                target_path = dest / new_filename

                with zip_ref.open(file_info) as source:
                    target_path.write_bytes(source.read())

                result.append(target_path)

    return result


def save_playbook_into_zip(playbook_name: str, data: dict[str, Any], dest: Path) -> Path:
    """Save raw playbook data into a ZIP file.

    Args:
        playbook_name: The name of the playbook to save.
        data: The raw playbook data to save.
        dest: The directory where the ZIP file should be saved.

    Returns:
        Path: The path to the saved ZIP file.

    """
    zip_bytes = base64.b64decode(data["blob"])
    zip_path = dest / f"{to_snake_case(playbook_name)}.zip"

    zip_path.write_bytes(zip_bytes)
    rich.print(f"Downloaded playbook file saved as: {zip_path}")

    return zip_path
