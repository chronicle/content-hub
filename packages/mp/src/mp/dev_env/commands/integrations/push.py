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

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import rich
import typer

from mp.dev_env.commands.push import push_app
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

from . import utils
from .minor_version_bump import minor_version_bump

if TYPE_CHECKING:
    from mp.dev_env.api import BackendAPI


@push_app.command(name="integration")
@track_command
def push_integration(
    integration: Annotated[
        str,
        typer.Argument(help="Integration to build and push."),
    ],
    *,
    is_staging: Annotated[
        bool,
        typer.Option("--staging", help="Push integration in to staging mode."),
    ] = False,
    custom: Annotated[
        bool,
        typer.Option(help="Push integration from the custom repository."),
    ] = False,
) -> None:
    """Build and push an integration to the dev environment (playground).

    Args:
        integration: The integration to build and push.
        is_staging: Add this option to push integration in to staging mode.
        custom: Add this option to push integration from the custom repository.

    """
    utils.build_integration(integration, custom=custom)

    zip_path: Path = _zip_integration(integration, custom=custom)

    _push_zip_to_soar(zip_path, is_staging=is_staging)


def _zip_integration(integration: str, *, custom: bool) -> Path:
    source_path: Path = utils.get_integration_path(integration, custom=custom)
    identifier: str = utils.get_integration_identifier(source_path)
    built_dir: Path = utils.find_built_integration_dir(identifier, custom=custom)
    minor_version_bump(built_dir, source_path, identifier)
    zip_path: Path = utils.zip_integration_dir(built_dir, custom=custom)
    rich.print(f"Zipped built integration at {zip_path}")
    return zip_path


def _push_zip_to_soar(zip_path: Path, *, is_staging: bool) -> None:
    config = load_dev_env_config()
    backend_api: BackendAPI = get_backend_api(config)

    try:
        details = backend_api.get_integration_details(zip_path, is_staging=is_staging)
        result = backend_api.upload_integration(
            zip_path, details["identifier"], is_staging=is_staging
        )
        zip_path.unlink()
        rich.print(f"Upload result: {result}")
        rich.print("[green]✅ Integration pushed successfully.[/green]")

    except Exception as e:
        error_message = f"Upload failed for {zip_path.stem}: {e}"
        rich.print(f"[red]{error_message}[/red]")
        raise typer.Exit(1) from e


@push_app.command(name="custom-integration-repository")
@track_command
def push_custom_integration_repository() -> None:
    """Build, zip, and upload the entire custom integration repository."""
    utils.build_integrations_custom_repository()
    zipped_paths = utils.zip_integration_custom_repository()
    _push_custom_integrations(zipped_paths)


def _push_custom_integrations(zipped_paths: list[Path]) -> None:
    config = load_dev_env_config()
    backend_api = get_backend_api(config)
    results: list[str] = []

    for zip_path in zipped_paths:
        try:
            details = backend_api.get_integration_details(zip_path)
            backend_api.upload_integration(zip_path, details["identifier"])
            rich.print(f"[green]Successfully pushed: {zip_path.name}[/green]")

        except Exception as e:  # noqa: BLE001
            results.append(f"{zip_path.name}: {e}")

    if results:
        rich.print("\n[bold red]Upload errors detected:[/bold red]")
        for error in results:
            rich.print(f"  - {error}")
        raise typer.Exit(1)
