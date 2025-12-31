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
from typing import Annotated, NamedTuple

import rich
import typer

from mp.telemetry import track_command

from . import utils
from .commands.integrations.integrations_command import push_integration
from .commands.push import push_app

__all__: list[str] = ["app", "deploy", "login"]

app: typer.Typer = typer.Typer(
    help="Commands for interacting with the development environment (playground)"
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
        utils.get_backend_api(config)
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
