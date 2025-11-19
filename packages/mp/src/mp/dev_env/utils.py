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
from pathlib import Path

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.integrations.integration import Integration

CONFIG_PATH: Path = Path.home() / ".mp_dev_env.json"


def zip_integration_dir(integration_dir: Path) -> Path:
    """Zip the contents of a built integration directory for upload.

    Args:
        integration_dir: Path to the built integration directory.

    Returns:
        Path: The path to the created zip file.

    """
    return Path(shutil.make_archive(str(integration_dir), "zip", integration_dir))


def load_dev_env_config() -> dict[str, str]:
    """Load the dev environment configuration from the config file.

    Returns:
        dict: The loaded configuration.

    Raises:
        typer.Exit: If the config file does not exist.

    """
    if not CONFIG_PATH.exists():
        rich.print("[red] Not logged in. Please run 'mp dev-env login' first. [/red]")
        raise typer.Exit(1)
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def build_integration(integration: str) -> None:
    """Invoke the build command for a single integration.

    Args:
        integration: The name of the integration to build.

    Raises:
        typer.Exit: If the build fails.

    """
    result = subprocess.run(  # noqa: S603
        ["mp", "build", "--integration", integration, "--quiet"],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        rich.print(f"[red]Build failed:\n{result.stderr}[/red]")
        raise typer.Exit(result.returncode)

    rich.print(f"Build output:\n{result.stdout}")


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


def find_built_integration_dir(identifier: str) -> Path:
    """Find the built integration directory.

    Args:
        identifier: The integration identifier.

    Returns:
        Path: The path to the built integration directory.

    Raises:
        typer.Exit: If the built integration is not found.

    """
    root: Path = mp.core.file_utils.create_or_get_out_integrations_dir()
    for repo in mp.core.constants.INTEGRATIONS_TYPES:
        candidate = root / repo / identifier
        if candidate.exists():
            return candidate

    rich.print(
        f"[red]Built integration not found for identifier '{identifier}'"
        " in out/content/integrations.[/red]"
    )
    raise typer.Exit(1)
