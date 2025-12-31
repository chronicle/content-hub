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

import shutil
import subprocess  # noqa: S404
from pathlib import Path

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.integrations.integration import Integration


def zip_integration_dir(integration_dir: Path) -> Path:
    """Zip the contents of a built integration directory for upload.

    Args:
        integration_dir: Path to the built integration directory.

    Returns:
        Path: The path to the created zip file.

    """
    return Path(shutil.make_archive(str(integration_dir), "zip", integration_dir))


def zip_integration_custom_repository() -> list[Path]:
    """Zip the contents of the custom repository for upload.

    Returns:
        list[Path]: List of paths to the created zip file.

    """
    custom_repo_out_dir: Path = (
        mp.core.file_utils.create_or_get_out_integrations_dir() / mp.core.constants.CUSTOM_REPO_NAME
    )
    return [
        zip_integration_dir(integration_path)
        for integration_path in custom_repo_out_dir.iterdir()
        if integration_path.is_dir()
    ]


def build_integration(integration: str, *, custom_integration: bool = False) -> None:
    """Invoke the build command for a single integration.

    Args:
        integration: The name of the integration to build.
        custom_integration: build integration from the custom repository.

    Raises:
        typer.Exit: If the build fails.

    """
    command: list[str] = ["mp", "build", "--integration", integration, "--quiet"]
    if custom_integration:
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


def find_built_integration_dir(identifier: str, *, custom_integration: bool = False) -> Path:
    """Find the built integration directory.

    Args:
        identifier: The integration identifier.
        custom_integration: search integration in out folder of custom repository.


    Returns:
        Path: The path to the built integration directory.

    Raises:
        typer.Exit: If the built integration is not found.

    """
    root: Path = mp.core.file_utils.create_or_get_out_integrations_dir()
    if custom_integration:
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


def get_integration_path(integration: str, *, custom_integration: bool = False) -> Path:
    """Find the source path for a given integration.

    Args:
        integration: The name of the integration to find.
        custom_integration: Whether to search in the custom repository.

    Returns:
        The path to the integration's source directory.

    Raises:
        typer.Exit: If the integration directory is not found.

    """
    integrations_root: Path = mp.core.file_utils.create_or_get_integrations_dir()
    if custom_integration:
        source_path = integrations_root / mp.core.constants.CUSTOM_REPO_NAME / integration
        if source_path.exists():
            return source_path

    for repo, folders in mp.core.constants.INTEGRATIONS_DIRS_NAMES_DICT.items():
        if repo == mp.core.constants.THIRD_PARTY_REPO_NAME:
            for folder in folders:
                if folder == mp.core.constants.POWERUPS_DIR_NAME:
                    candidate: Path = integrations_root / folder / integration
                else:
                    candidate: Path = integrations_root / repo / folder / integration
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
