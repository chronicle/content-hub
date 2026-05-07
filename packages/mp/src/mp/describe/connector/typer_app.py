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
import logging
import pathlib  # noqa: TC003
from typing import Annotated

import typer

import mp.core.config

from .describe import DescribeConnector
from .describe_all import describe_all_connectors

logger: logging.Logger = logging.getLogger(__name__)


app = typer.Typer(help="Describe connectors in the marketplace.")


@app.command(
    name="connector",
    help="Describe connectors in an integration or across the entire marketplace using Gemini.",
    no_args_is_help=True,
)
def describe(  # noqa: PLR0913
    connectors: Annotated[list[str] | None, typer.Argument(help="Connector names")] = None,
    integration: Annotated[str | None, typer.Option("-i", "--integration", help="Integration name")] = None,
    *,
    all_marketplace: Annotated[
        bool,
        typer.Option(
            "-a",
            "--all",
            help="Describe all integrations in the marketplace, or all connectors if an integration is specified",
        ),
    ] = False,
    src: Annotated[
        pathlib.Path | None,
        typer.Option(help="The path to the marketplace. If not provided, the configured path will be used."),
    ] = None,
    dst: Annotated[
        pathlib.Path | None,
        typer.Option(
            help="The path to save the descriptions to. If not provided, they will be saved in the marketplace."
        ),
    ] = None,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Whether to override existing descriptions.")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
) -> None:
    """Describe connectors in a given integration.

    Args:
        connectors: The names of the connectors to describe.
        integration: The name of the integration to describe connectors for.
        all_marketplace: Whether to describe all integrations or all connectors for the integration.
        src: The path to the marketplace.
        dst: The path to save the descriptions to.
        override: Whether to override existing descriptions.
        quiet: Log less on runtime.
        verbose: Log more on runtime.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    sem = asyncio.Semaphore(mp.core.config.get_gemini_concurrency())
    if integration:
        target_connector_file_names: set[str] = set(connectors) if connectors else set()
        if all_marketplace:
            target_connector_file_names = set()

        asyncio.run(
            DescribeConnector(
                integration,
                target_connector_file_names,
                src=src,
                dst=dst,
                override=override,
            ).describe(sem=sem)
        )
    elif all_marketplace:
        asyncio.run(describe_all_connectors(src=src, dst=dst, override=override))
    else:
        logger.error("Please specify either --integration or --all")
        raise typer.Exit(code=1)
