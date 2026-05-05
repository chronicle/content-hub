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

import logging
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from mp.pack.flow.integrations.flow import pack_integration as flow_pack_integration
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer()


@app.command(name="integration", help="Pack an integration into a SOAR supported ZIP")
@track_command
def pack_integration(
    integration: Annotated[
        str,
        typer.Argument(help="The name of the integration to pack."),
    ],
    *,
    version: Annotated[
        str | None,
        typer.Option(
            "--version",
            "-v",
            help="Old version to fetch from the repo and create the ZIP.",
        ),
    ] = None,
    beta: Annotated[
        str | None,
        typer.Option(
            "--beta",
            "-b",
            help="Name of the custom beta integration.",
        ),
    ] = None,
    zip_dst: Annotated[
        Path | None,
        typer.Option(
            "--dst",
            "-d",
            help="Destination directory to save the ZIP file. Defaults to 'out' directory.",
        ),
    ] = None,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive/--non-interactive",
            help="Enable or disable interactive component selection.",
        ),
    ] = True,
) -> None:
    """Run the `mp pack integration` command.

    Args:
        integration: The name of the integration to pack.
        version: Old version to fetch from the repo.
        beta: Name of the custom beta integration.
        zip_dst: Destination directory to save the ZIP file.
        interactive: Enable or disable interactive component selection.

    Raises:
        typer.Exit: If an error occurs during the packing process.

    """
    try:
        flow_pack_integration(
            integration_name=integration,
            version=version,
            beta_name=beta,
            zip_dst=zip_dst,
            interactive=interactive,
        )
    except Exception as e:
        logger.exception("Error occurred during integration packing")
        raise typer.Exit(code=1) from e
