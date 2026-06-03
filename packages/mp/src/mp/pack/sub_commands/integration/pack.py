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

from mp.pack.flow.integrations.flow import PackConfig
from mp.pack.flow.integrations.flow import pack_integration as flow_pack_integration
from mp.telemetry import track_command

logger: logging.Logger = logging.getLogger(__name__)

app: typer.Typer = typer.Typer()


@app.command(name="integration", help="Pack an integration into a SOAR supported ZIP")
@track_command
def pack_integration(  # noqa: PLR0913
    integration: Annotated[
        str,
        typer.Argument(help="The name of the integration to pack."),
    ],
    *,
    source: Annotated[
        Path | None,
        typer.Option(
            "--src",
            help=(
                "Source directory containing the integration. "
                "If not specified, the command will search for the integration in the default 'content' directory."
            ),
        ),
    ] = None,
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

    This command packs a specified integration into a SOAR-supported ZIP file.
    It can be configured to use a specific source directory, pack a certain version,
    apply a beta name, and specify an output directory for the ZIP file.

    Args:
        integration: The name of the integration to pack.
        source: Source directory containing the integration. If not provided,
                the command searches in the default 'content' directory.
        version: If specified, fetches the integration version from the repo.
        beta: If specified, applies a custom beta name to the integration.
        zip_dst: The destination directory for the created ZIP file.
                 Defaults to the 'out/pack' directory.
        interactive: Enables or disables the interactive component selection.
                     Defaults to True.

    Raises:
        typer.Exit: If an error occurs during the packing process.

    """
    try:
        flow_pack_integration(
            integration_name=integration,
            config=PackConfig(
                src=source,
                version=version,
                beta_name=beta,
                zip_dst=zip_dst,
                interactive=interactive,
            ),
        )
    except Exception as e:
        logger.exception("Error occurred during integration packing")
        raise typer.Exit(code=1) from e
