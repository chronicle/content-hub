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

from .describe import DescribeIntegration
from .describe_all import describe_all_integrations

app = typer.Typer(help="Commands for describing integrations")


@app.command(
    name="integration",
    help="Describe integrations using Gemini.",
    epilog=(
        "Examples:\n\n"
        "    $ mp describe integration aws_ec2\n\n"
        "    $ mp describe integration --all\n\n"
        "    $ mp describe integration --all --src ./custom_folder\n\n"
    ),
    no_args_is_help=True,
)
def describe(  # noqa: PLR0913
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Describe all integrations in the marketplace",
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
            help="Rewrite integrations that already have their description.",
        ),
    ] = False,
) -> None:
    """Describe integrations.

    Args:
        integrations: The names of the integrations.
        all_marketplace: Whether to describe all integrations in the marketplace.
        src: Customize the source folder to describe from.
        dst: Customize destination folder to save the AI descriptions.
        quiet: Quiet log options.
        verbose: Verbose log options.
        override: Whether to rewrite existing descriptions.

    Raises:
        typer.Exit: If neither integrations nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if integrations:
        sem: asyncio.Semaphore = asyncio.Semaphore(mp.core.config.get_gemini_concurrency())
        for integration in integrations:
            asyncio.run(
                DescribeIntegration(integration, src=src, dst=dst, override=override).describe(
                    sem=sem
                )
            )
    elif all_marketplace:
        asyncio.run(describe_all_integrations(src=src, dst=dst, override=override))
    else:
        rich.print("[red]Please specify either integrations or --all[/red]")
        raise typer.Exit(code=1)
