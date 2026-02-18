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

import dataclasses
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import typer

import mp.core.config
from mp.build_project.flow.integrations.flow import build_integrations
from mp.core.utils import (
    ensure_valid_list,
)
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.core.config import RuntimeParams

app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class BuildParams:
    integrations: list[str]
    deconstruct: bool
    custom_integration: bool
    src: Path | None
    dst: Path | None

    def validate(self) -> None:
        """Validate the parameters.

        Validates the provided parameters
        to ensure proper usage of mutually exclusive
        options and constraints.
        Handles error messages and raises exceptions if validation fails.

        Raises:
            typer.BadParameter:
                If parameters are not provided correctly.

        """
        msg: str
        if len(self.integrations) == 0:
            msg = "At least one integration name need to be provided."
            raise typer.BadParameter(msg)

        if self.custom_integration and self.deconstruct:
            msg = "Cannot use --deconstruct and --custom_integration."
            raise typer.BadParameter(msg)

        if self.src and self.custom_integration:
            msg = "Cannot use --src and --custom_integration."
            raise typer.BadParameter(msg)

        if self.dst and self.custom_integration:
            msg = "Cannot use --dst and --custom_integration."
            raise typer.BadParameter(msg)


@app.command(name="integration", help="Build content-hub response integrations")
@track_command
def build_integration(  # noqa: PLR0913
    integrations: Annotated[
        list[str],
        typer.Argument(
            help="Build the specified integrations",
            default_factory=list,
        ),
    ],
    src: Annotated[
        Path | None,
        typer.Option(help="Customize source folder to build or deconstruct from."),
    ] = None,
    dst: Annotated[
        Path | None,
        typer.Option(help="Customize destination folder to build or deconstruct to."),
    ] = None,
    *,
    deconstruct: Annotated[
        bool,
        typer.Option(
            "--deconstruct",
            "-d",
            help="Deconstruct built integrations instead of building them.",
        ),
    ] = False,
    custom_integration: Annotated[
        bool,
        typer.Option(
            help="Build a specific integration from the custom repository.",
        ),
    ] = False,
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
) -> None:
    """Run the `mp build integration` command.

    Args:
        integrations: the integrations to build
        src: Customize source folder to build from.
        dst: Customize destination folder to build to.
        deconstruct: whether to deconstruct instead of build
        custom_integration: if need to build integration from the custom repo.
        quiet: quiet log options
        verbose: Verbose log options

    """
    integrations = ensure_valid_list(integrations)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: BuildParams = BuildParams(
        integrations=integrations,
        deconstruct=deconstruct,
        custom_integration=custom_integration,
        src=src,
        dst=dst,
    )
    params.validate()
    if src:
        mp.core.config.set_custom_src(src)
    if dst:
        mp.core.config.set_custom_dst(dst)

    try:
        if integrations:
            build_integrations(
                integrations=integrations,
                repositories=[],
                src=src,
                dst=dst,
                deconstruct=deconstruct,
                custom_integration=custom_integration,
            )

    finally:
        mp.core.config.clear_custom_src()
        mp.core.config.clear_custom_dst()
