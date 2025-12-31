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
from typing import TYPE_CHECKING, Annotated, NamedTuple

import rich
import typer

import mp.core.constants
import mp.core.file_utils
from mp.telemetry import track_command

from . import api, utils
from .minor_version_bump import minor_version_bump

if TYPE_CHECKING:
    from pathlib import Path

__all__: list[str] = ["app", "deploy", "login"]

app: typer.Typer = typer.Typer(
    help="Commands for interacting with the development environment (playground)"
)

push_app: typer.Typer = typer.Typer(
    help="Push integrations or repositories to the SOAR environment."
)
app.add_typer(push_app, name="push")


class DevEnvParams(NamedTuple):
    api_root: str
    username: str | None
    password: str | None
    api_key: str | None


@app.command()
@track_command
def login(
    api_root: Annotated[str | None, typer.Option(help="API root URL.")] = None,
    username: Annotated[str | None, typer.Option(help="Authentication username.")] = None,
    password: Annotated[
        str | None, typer.Option(help="Authentication password.", hide_input=True)
    ] = None,
    api_key: Annotated[
        str | None, typer.Option(help="Authentication API key.", hide_input=True)
    ] = None,
    *,
    no_verify: Annotated[bool, typer.Option(help="Skip verification after saving.")] = False,
) -> None:
    """Authenticate to the dev environment (playground).

    Args:
        api_root: The API root of the dev environment.
        username: The username to authenticate with.
        password: The password to authenticate with.
        api_key: The API key for authentication.
        no_verify: Skip credential verification after saving.

    Raises:
        typer.Exit: If the API root, username, or password is not provided.

    """
    if api_root is None:
        api_root = typer.prompt("API root (e.g. https://playground.example.com)")

    if api_key is not None:
        username = None
        password = None
    else:
        if username is None:
            username = typer.prompt("Username")
        if password is None:
            password = typer.prompt("Password", hide_input=True)

    if api_root is None:
        rich.print("[red]API root is required.[/red]")
        raise typer.Exit(1)

    params = DevEnvParams(username=username, password=password, api_key=api_key, api_root=api_root)
    config = params._asdict()

    with utils.CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f)
    rich.print(f"Credentials saved to {utils.CONFIG_PATH}")

    if not no_verify:
        _get_backend_api(config)
        rich.print("[green]✅ Credentials verified successfully.[/green]")


@app.command(
    deprecated=True,
    help="Deprecated. Please use 'dev-env push integration' instead.",
)
@track_command
def deploy(
    integration: str = typer.Argument(help="Integration to build and deploy."),
    *,
    is_staging: bool = False,
) -> None:
    """Deprecated."""  # noqa: D401
    rich.print("[yellow]Note: 'deploy' is deprecated. Use 'push integration' instead.[/yellow]")
    push_integration(integration, is_staging=is_staging)


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
    config = utils.load_dev_env_config()
    source_path = _get_integration_path(integration, custom_integration=custom_integration)
    identifier = utils.get_integration_identifier(source_path)

    utils.build_integration(integration, custom_integration=custom_integration)
    built_dir = utils.find_built_integration_dir(identifier, custom_integration=custom_integration)
    minor_version_bump(built_dir, source_path, identifier)

    zip_path = utils.zip_integration_dir(built_dir)
    rich.print(f"Zipped built integration at {zip_path}")

    backend_api = _get_backend_api(config)
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
    config = utils.load_dev_env_config()
    utils.build_integrations_custom_repository()
    zipped_paths = utils.zip_integration_custom_repository()

    backend_api = _get_backend_api(config)
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


def _get_backend_api(config: dict[str, str]) -> api.BackendAPI:
    try:
        if config.get("api_key"):
            backend_api = api.BackendAPI(api_root=config["api_root"], api_key=config["api_key"])
        else:
            backend_api = api.BackendAPI(
                api_root=config["api_root"],
                username=config["username"],
                password=config["password"],
            )
            backend_api.login()

        return backend_api  # noqa: TRY300

    except Exception as e:
        rich.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1) from e


def _get_integration_path(integration: str, *, custom_integration: bool = False) -> Path:
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
