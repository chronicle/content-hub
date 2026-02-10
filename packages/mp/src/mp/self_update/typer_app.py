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

import logging
import sys

import typer

from mp.core import unix

UPDATE_URL: str = "git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp"

self_app: typer.Typer = typer.Typer(help="Manage the mp tool itself.")
logger: logging.Logger = logging.getLogger("mp.self")


@self_app.command(name="update")
def update() -> None:
    """Update mp to the latest version.

    Raises:
        typer.Exit: If the update fails.

    """
    typer.echo("Updating mp...")
    command: list[str] = [
        sys.executable,
        "-m",
        "uv",
        "pip",
        "install",
        "--upgrade",
        UPDATE_URL,
    ]
    try:
        unix.execute_command_and_get_output(command, [])
        logger.info("[green]Successfully updated mp![/green]")
    except unix.FatalCommandError:
        logger.exception("[red]Failed to update mp.[/red]")
        raise typer.Exit(code=1) from None
