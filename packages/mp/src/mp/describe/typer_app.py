# Copyright 2026 Google LLC
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

import asyncio
import pathlib  # noqa: TC003
from typing import Annotated

import rich
import typer

import mp.core.config

from .action.typer_app import app as action_app
from .all_content import describe_all_content
from .connector.typer_app import app as connector_app
from .integration.typer_app import app as integration_app
from .job.typer_app import app as job_app

app: typer.Typer = typer.Typer(help="Commands for creating description for content using Gemini")

app.add_typer(action_app)
app.add_typer(connector_app)
app.add_typer(integration_app)
app.add_typer(job_app)


@app.command(
    name="all-content",
    help=(
        "Describe all content (actions, connectors, jobs, and the integration) for integrations."
    ),
    no_args_is_help=True,
)
def all_content(  # noqa: PLR0913
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Describe all content for all integrations in the marketplace",
        ),
    ] = False,
    src: Annotated[
        pathlib.Path | None,
        typer.Option(help="Customize source folder to describe from."),
    ] = None,
    dst: Annotated[
        pathlib.Path | None,
        typer.Option(help="Customize destination folder to save the AI descriptions."),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Log less on runtime.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Log more on runtime.",
        ),
    ] = False,
    override: Annotated[
        bool,
        typer.Option(
            "--override",
            "-o",
            help="Rewrite content that already have their description.",
        ),
    ] = False,
) -> None:
    """Describe all content in integrations.

    Raises:
        typer.Exit: If neither integrations nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if integrations and not all_marketplace:
        asyncio.run(
            describe_all_content(src=src, dst=dst, override=override, integrations=integrations)
        )
    elif all_marketplace:
        asyncio.run(describe_all_content(src=src, dst=dst, override=override))
    else:
        rich.print("[red]Please specify either an integration or --all[/red]")
        raise typer.Exit(code=1)
