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

from typing import Annotated

import rich
import typer

from mp.dev_env.commands.push import push_app
from mp.dev_env.minor_version_bump import minor_version_bump
from mp.dev_env.utils import get_backend_api, load_dev_env_config
from mp.telemetry import track_command

from . import utils


@push_app.command(name="integration")
@track_command
def push_integration(
    integration: str = typer.Argument(help="Integration to build and deploy."),
    *,
    is_staging: Annotated[
        bool,
        typer.Option("--staging", help="Deploy integration in to staging mode."),
    ] = False,
    custom_integration: Annotated[
        bool,
        typer.Option(help="Deploy integration from the custom repository."),
    ] = False,
) -> None:
    """Build and deploy an integration to the dev environment (playground).

    Args:
        integration: The integration to build and deploy.
        is_staging: Add this option to deploy integration in to staging mode.
        custom_integration: Add this option to deploy integration from the custom repository.

    Raises:
        typer.Exit: If the integration is not found.

    """
    config = load_dev_env_config()
    source_path = utils.get_integration_path(integration, custom_integration=custom_integration)
    identifier = utils.get_integration_identifier(source_path)

    utils.build_integration(integration, custom_integration=custom_integration)
    built_dir = utils.find_built_integration_dir(identifier, custom_integration=custom_integration)
    minor_version_bump(built_dir, source_path, identifier)

    zip_path = utils.zip_integration_dir(built_dir)
    rich.print(f"Zipped built integration at {zip_path}")

    backend_api = get_backend_api(config)
    try:
        details = backend_api.get_integration_details(zip_path, is_staging=is_staging)
        result = backend_api.upload_integration(
            zip_path, details["identifier"], is_staging=is_staging
        )
        rich.print(f"Upload result: {result}")
        rich.print("[green]✅ Integration deployed successfully.[/green]")
    except Exception as e:
        rich.print(f"[red]Upload failed: {e}[/red]")
        raise typer.Exit(1) from e


@push_app.command(name="custom-integration-repository")
@track_command
def push_custom_integration_repository() -> None:
    """Build, zip, and upload the entire custom integration repository.

    Raises:
        typer.Exit: If authentication fails or any individual uploads fail.

    """
    config = load_dev_env_config()
    utils.build_integrations_custom_repository()
    zipped_paths = utils.zip_integration_custom_repository()

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
