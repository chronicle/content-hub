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
import shutil
import subprocess  # noqa: S404
import zipfile
from pathlib import Path
from typing import Any

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.integrations.integration import Integration
from mp.core.utils import to_snake_case


def get_integration_path(integration: str, *, custom: bool = False) -> Path:
    """Find the source path for a given integration.

    Args:
        integration: The name of the integration to find.
        custom: Whether to search in the custom repository.

    Returns:
        The path to the integration's source directory.

    Raises:
        typer.Exit: If the integration directory is not found.

    """
    integrations_root: Path = mp.core.file_utils.create_or_get_integrations_dir()
    if custom:
        source_path = integrations_root / mp.core.constants.CUSTOM_REPO_NAME / integration
        if source_path.exists():
            return source_path

    for repo, folders in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT.items():
        if repo == mp.core.constants.THIRD_PARTY_REPO_NAME:
            for folder in folders:
                candidate: Path = integrations_root / repo / folder / integration
                if folder == mp.core.constants.POWERUPS_DIR_NAME:
                    candidate: Path = integrations_root / folder / integration

                if candidate.exists():
                    return candidate
        else:
            candidate: Path = integrations_root / repo / integration
            if candidate.exists():
                return candidate

    rich.print(
        f"[red]Could not find source integration at {integrations_root}/.../{integration}[/red]"
    )
    raise typer.Exit(1)


def get_integration_identifier(source_path: Path) -> str:
    """Get the integration identifier from the non-built integration path.

    Args:
        source_path: Path to the integration source directory.

    Returns:
        str: The integration identifier.

    Raises:
        typer.Exit: If the identifier cannot be determined.

    """
    try:
        integration_obj = Integration.from_non_built_path(source_path)
    except ValueError as e:
        rich.print(f"[red]Could not determine integration identifier: {e}[/red]")
        raise typer.Exit(1) from e
    else:
        return integration_obj.identifier


def build_integration(integration: str, *, custom: bool = False) -> None:
    """Invoke the build command for a single integration.

    Args:
        integration: The name of the integration to build.
        custom: build integration from the custom repository.

    Raises:
        typer.Exit: If the build fails.

    """
    command: list[str] = ["mp", "build", "--integration", integration, "--quiet"]
    if custom:
        command.append("--custom-integration")
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


def find_built_integration_dir(identifier: str, *, custom: bool = False) -> Path:
    """Find the built integration directory.

    Args:
        identifier: The integration identifier.
        custom: search integration in the out folder of custom repository.


    Returns:
        Path: The path to the built integration directory.

    Raises:
        typer.Exit: If the built integration is not found.

    """
    root: Path = mp.core.file_utils.create_or_get_out_integrations_dir()
    if custom:
        candidate = root / mp.core.constants.CUSTOM_REPO_NAME / identifier
        if candidate.exists():
            return candidate

    for repo in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT:
        candidate: Path = root / repo / identifier
        if candidate.exists():
            return candidate

    rich.print(
        f"[red]Built integration not found for identifier '{identifier}'"
        " in out/content/integrations.[/red]"
    )
    raise typer.Exit(1)


def zip_integration_dir(integration_dir: Path, *, custom: bool = False) -> Path:
    """Zip the contents of a built integration directory for upload.

    Args:
        integration_dir: Path to the built integration directory.
        custom: Whether the integration is from the custom repository.

    Returns:
        Path: The path to the created zip file.

    """
    if custom:
        _change_integration_to_custom(integration_dir)

    return Path(shutil.make_archive(str(integration_dir), "zip", integration_dir))


def build_integrations_custom_repository() -> None:
    """Build command for all integrations in the custom repository.

    Raises:
        typer.Exit: If the build fails.

    """
    command: list[str] = ["mp", "build", "-r", "custom"]
    result = subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        rich.print(f"[red]Build failed:\n{result.stderr}[/red]")
        raise typer.Exit(result.returncode)


def zip_integration_custom_repository() -> list[Path]:
    """Zip the contents of the custom repository for upload.

    Returns:
        list[Path]: List of paths to the created zip file.

    """
    custom_repo_out_dir: Path = (
        mp.core.file_utils.create_or_get_out_integrations_dir() / mp.core.constants.CUSTOM_REPO_NAME
    )

    for integration in custom_repo_out_dir.iterdir():
        _change_integration_to_custom(integration)

    return [
        zip_integration_dir(integration_path)
        for integration_path in custom_repo_out_dir.iterdir()
        if integration_path.is_dir()
    ]


def _change_integration_to_custom(built_path: Path) -> None:
    for file in built_path.iterdir():
        if file.name == mp.core.constants.INTEGRATION_DEF_FILE.format(built_path.name):
            _modify_def_file_to_custom(
                built_path / mp.core.constants.INTEGRATION_DEF_FILE.format(built_path.name)
            )
    if (built_path / mp.core.constants.OUT_ACTIONS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_ACTIONS_META_DIR,
            mp.core.constants.ACTIONS_META_SUFFIX,
        )
    if (built_path / mp.core.constants.OUT_CONNECTORS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_CONNECTORS_META_DIR,
            mp.core.constants.CONNECTORS_META_SUFFIX,
        )
    if (built_path / mp.core.constants.OUT_JOBS_META_DIR).exists():
        _modify_def_files_to_custom(
            built_path / mp.core.constants.OUT_JOBS_META_DIR, mp.core.constants.JOBS_META_SUFFIX
        )


def _modify_def_files_to_custom(def_files_dir: Path, suffix: str) -> None:
    for file in def_files_dir.iterdir():
        if file.suffix == suffix:
            _modify_def_file_to_custom(file)


def _modify_def_file_to_custom(file: Path) -> None:
    try:
        with Path.open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["IsCustom"] = True

        with Path.open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    except (OSError, json.JSONDecodeError) as e:
        rich.print(f"Failed to process {file}: {e}")


def save_integration_as_zip(integration_name: str, resp: Any, dst: Path) -> Path:
    """Save raw integration data into a ZIP file.

    Args:
        integration_name: The name of the integration to save.
        resp: The raw integration data to save.
        dst: The directory where the ZIP file should be saved.

    Returns:
        Path: The path to the saved ZIP file.

    """
    zip_path = dst / f"{integration_name}.zip"
    zip_path.write_bytes(resp.content)
    return zip_path


def unzip_integration(zip_path: Path, temp_path: Path) -> Path:
    """Unzips an integration to a destination.

    Args:
        zip_path: The path to the source ZIP file.
        temp_path: temp path that the built integration will be extracted to.

    Returns:
        A path to the successfully extracted folder.

    """
    dest: Path = temp_path / zip_path.stem
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dest)
    return dest


def deconstruct_integration(built_integration: Path, dst: Path) -> Path:
    """Deconstructs a built integration and restores the source to its original directory.

    Args:
        built_integration (Path): Path to the built integration folder.
        dst (Path): Destination folder.

    Returns:
        Path: Path to the deconstructed integration.

    Raises:
        typer.Exit: If the deconstruction subprocess fails.

    """
    command: list[str] = [
        "mp",
        "build",
        "-i",
        built_integration.stem,
        "--src",
        f"{built_integration.parent}",
        "--dst",
        f"{dst}",
        "-d",
    ]
    result = subprocess.run(  # noqa: S603
        command, capture_output=True, check=False, text=True
    )
    if result.returncode != 0:
        rich.print(f"[red]Deconstruct failed:\n{result.stderr}[/red]")
        raise typer.Exit(result.returncode)

    return dst / to_snake_case(built_integration.stem)
