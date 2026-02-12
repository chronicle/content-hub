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

from .describe import DescribeAction
from .describe_all import describe_all_actions

app = typer.Typer(help="Commands for describing actions")


@app.command(
    name="action",
    help="Describe actions in an integration or across the entire marketplace using Gemini.",
    epilog=(
        "Examples:\n\n"
        "    $ mp describe action ping get_logs -i aws_ec2\n\n"
        "    $ mp describe action -i aws_ec2 --all\n\n"
        "    $ mp describe action --all\n\n"
        "    $ mp describe action --all --src ./custom_folder\n\n"
    ),
    no_args_is_help=True,
)
def describe(  # noqa: PLR0913
    actions: Annotated[list[str] | None, typer.Argument(help="Action names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help=(
                "Describe all integrations in the marketplace, or all actions if an"
                " integration is specified"
            ),
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
            help="Rewrite actions that already have their description.",
        ),
    ] = False,
) -> None:
    """Describe actions in a given integration.

    Args:
        integration: The name of the integration.
        actions: The names of the actions to describe.
        all_marketplace: Whether to describe all integrations in the marketplace.
        src: Customize the source folder to describe from.
        dst: Customize destination folder to save the AI descriptions.
        quiet: Quiet log options.
        verbose: Verbose log options.
        override: Whether to rewrite existing descriptions.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if integration:
        target_action_file_names: set[str] = set(actions) if actions else set()
        if all_marketplace:
            target_action_file_names = set()

        sem: asyncio.Semaphore = asyncio.Semaphore(mp.core.config.get_gemini_concurrency())
        asyncio.run(
            DescribeAction(
                integration, target_action_file_names, src=src, dst=dst, override=override
            ).describe_actions(sem=sem)
        )
    elif all_marketplace:
        asyncio.run(describe_all_actions(src=src, dst=dst, override=override))
    else:
        rich.print("[red]Please specify either --integration or --all[/red]")
        raise typer.Exit(code=1)
