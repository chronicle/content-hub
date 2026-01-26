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
from typing import Annotated

import rich
import typer

from .describe import DescribeAction
from .describe_all import describe_all_actions

app = typer.Typer(help="Commands for describing actions")


@app.command(name="action")
def describe(
    actions: Annotated[list[str] | None, typer.Argument(help="Action names")] = None,
    integration: Annotated[
        str | None, typer.Option("-i", "--integration", help="Integration name")
    ] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("--all", help="Describe all integrations in the marketplace")
    ] = False,
) -> None:
    """Describe actions in a given integration.

    Args:
        integration: The name of the integration.
        actions: The names of the actions to describe.
        all_marketplace: Whether to describe all integrations in the marketplace.

    Raises:
        typer.Exit: If neither --integration nor --all is specified.

    """
    if all_marketplace:
        asyncio.run(describe_all_actions())
    elif integration:
        target_actions = set(actions) if actions else set()
        asyncio.run(DescribeAction(integration, target_actions).describe_actions())
    else:
        rich.print("[red]Please specify either --integration or --all[/red]")
        raise typer.Exit(code=1)
