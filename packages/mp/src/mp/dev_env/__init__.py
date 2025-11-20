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


class DevEnvParams(NamedTuple):
    api_root: str
    username: str | None
    password: str | None
    api_key: str | None


@app.command(
    help=(
        "Set the login parameters for the SOAR environment you want to push response integrations"
        " to"
    )
)
@track_command
def login(
    api_root: Annotated[
        str | None,
        typer.Option(
            "--api-root",
            help="API root (e.g. https://playground.example.com). If not provided, will prompt.",
        ),
    ] = None,
    username: Annotated[
        str | None,
        typer.Option(
            "--username",
            help="Username for authentication. If not provided, will prompt.",
        ),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option(
            "--password",
            help="Password for authentication. If not provided, will prompt.",
            hide_input=True,
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            help="API key for authentication. If provided, username and password are not required.",
            hide_input=True,
        ),
    ] = None,
    *,
    no_verify: Annotated[
        bool,
        typer.Option(
            "--no-verify",
            help="Skip credential verification after saving.",
        ),
    ] = False,
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
        rich.print("API root is required.")
        raise typer.Exit(1)

    if api_key is None and (username is None or password is None):
        rich.print(
            "Either API key or both username and password are required. "
            "Please provide them using the --api-key option or "
            "--username and --password options. "
            "Or run 'mp dev-env login' to be prompted for them."
        )
        raise typer.Exit(1)

    params = DevEnvParams(username=username, password=password, api_key=api_key, api_root=api_root)
    config = {
        "api_root": params.api_root,
        "username": params.username,
        "password": params.password,
        "api_key": params.api_key,
    }
    with utils.CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f)
    rich.print(f"Credentials saved to {utils.CONFIG_PATH}")

    if not no_verify:
        try:
            if api_key is not None:
                backend_api = api.BackendAPI(api_root=params.api_root, api_key=params.api_key)
            else:
                backend_api = api.BackendAPI(
                    api_root=params.api_root, username=params.username, password=params.password
                )
            backend_api.login()
            rich.print("[green]✅ Credentials verified successfully.[/green]")
        except Exception as e:
            utils.CONFIG_PATH.unlink(missing_ok=True)
            rich.print(f"[red]Credential verification failed: {e}\nCredentials file removed.[/red]")
            raise typer.Exit(1) from e


@app.command(help="Deploy an integration to the SOAR environment configured by the login command.")
@track_command
def deploy(
    integration: str = typer.Argument(..., help="Integration to build and deploy."),
    *,
    is_staging: Annotated[
        bool,
        typer.Option("--staging", help="Add this option to deploy integration in to staging mode."),
    ] = False,
) -> None:
    """Build and deploy an integration to the dev environment (playground).

    Args:
        integration: The integration to build and deploy.
        is_staging: Add this option to deploy integration in to staging mode.

    Raises:
        typer.Exit: If the integration is not found.

    """
    config: dict[str, str] = utils.load_dev_env_config()
    source_path: Path = _get_integration_path(integration)
    identifier: str = utils.get_integration_identifier(source_path)

    utils.build_integration(integration)
    built_dir: Path = utils.find_built_integration_dir(identifier)
    minor_version_bump(built_dir, source_path, identifier)

    zip_path: Path = utils.zip_integration_dir(built_dir)
    rich.print(f"Zipped built integration at {zip_path}")

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
        details = backend_api.get_integration_details(zip_path, is_staging=is_staging)
        integration_id: str = details["identifier"]
        result = backend_api.upload_integration(zip_path, integration_id, is_staging=is_staging)
        rich.print(f"Upload result: {result}")
        rich.print("[green]✅ Integration deployed successfully.[/green]")

    except Exception as e:
        rich.print(f"[red]Upload failed: {e}[/red]")
        raise typer.Exit(1) from e


def _get_integration_path(integration: str) -> Path:
    source_path: Path | None = None
    integrations_root: Path = mp.core.file_utils.create_or_get_integrations_dir()
    for repo in mp.core.constants.INTEGRATIONS_TYPES:
        candidate: Path = integrations_root / repo / integration
        if candidate.exists():
            source_path = candidate
            break

    if not source_path or not source_path.exists():
        rich.print(
            f"[red]Could not find source integration "
            f"at {integrations_root}/{'|'.join(mp.core.constants.INTEGRATIONS_TYPES)}/{integration}"
            f"[/red]"
            "\nPlease ensure the content-hub path is properly configured."
            "\nYou can verify your configuration by running [bold]mp config"
            " --display-config[/bold]."
            "\nIf the path is incorrect, re-configure it by running [bold]mp config"
            " --root-path <your_path>[/bold]."
        )
        raise typer.Exit(1)

    return source_path
