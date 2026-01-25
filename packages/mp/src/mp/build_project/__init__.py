"""Package for building and deconstructing integration projects.

This package provides the `build` CLI command for processing integration
repositories, or individual integrations. It handles both building
integrations into a deployable format and deconstructing built integrations
back into their source structure. The package also includes modules for
managing the marketplace JSON, restructuring integration components (metadata,
scripts, code, dependencies), and defining an interface for restructurable
components.
"""

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
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

import mp.core.config
from mp.core.custom_types import RepositoryType
from mp.core.utils import (
    ensure_valid_list,
    should_preform_integration_logic,
    should_preform_playbook_logic,
)
from mp.telemetry import track_command

from .flow.integrations.flow import build_integrations
from .flow.playbooks.flow import build_playbooks

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.config import RuntimeParams

__all__: list[str] = ["app", "build"]
app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class BuildParams:
    repository: Iterable[RepositoryType]
    integrations: Iterable[str]
    playbooks: Iterable[str]
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
                If none of the required options (--repository,
                or --integration) are provided.
            typer.BadParameter:
                If more than one of the options (--repository,
                or --integration) is used at the same time.
            typer.BadParameter:
                If the --deconstruct option is used with any option
                other than --integration.

        """
        params: list[Iterable[str] | Iterable[RepositoryType]] = self._as_list()
        msg: str
        if not any(params):
            msg = "At least one of --repository, --integration, --playbook must be used."
            raise typer.BadParameter(msg)

        if sum(map(bool, params)) != 1:
            msg = "Only one of --repository, --integration, --playbook shall be used."
            raise typer.BadParameter(msg)

        if self.deconstruct and self.repository:
            msg = "--deconstruct works only with --integration or --playbook."
            raise typer.BadParameter(msg)

        if self.custom_integration and (
            self.repository or RepositoryType.PLAYBOOKS in self.repository
        ):
            msg = "--custom_integration works only with --integration."
            raise typer.BadParameter(msg)

        if self.custom_integration and self.deconstruct:
            msg = "Cannot use --deconstruct and --custom_integration."
            raise typer.BadParameter(msg)

        if self.src and self.custom_integration:
            msg = "Cannot use --src and --custom_integration."
            raise typer.BadParameter(msg)

        if self.dst and self.custom_integration:
            msg = "Cannot use --dst and --custom_integration."

    def _as_list(self) -> list[Iterable[RepositoryType] | Iterable[str]]:
        return [self.repository, self.integrations, self.playbooks]


@app.command(name="build", help="Build the marketplace")
@track_command
def build(  # noqa: PLR0913
    repositories: Annotated[
        list[RepositoryType],
        typer.Option(
            "--repository",
            "-r",
            help="Build all integrations in specified integration repositories",
            default_factory=list,
        ),
    ],
    integrations: Annotated[
        list[str],
        typer.Option(
            "--integration",
            "-i",
            help="Build a specified integration",
            default_factory=list,
        ),
    ],
    playbooks: Annotated[
        list[str],
        typer.Option(
            "--playbook",
            "-p",
            help="Build a specified playbook",
            default_factory=list,
        ),
    ],
    src: Annotated[
        Path | None,
        typer.Option("--src", help="Customize source folder to build or deconstruct from."),
    ] = None,
    dst: Annotated[
        Path | None,
        typer.Option("--dst", help="Customize destination folder to build or deconstruct to."),
    ] = None,
    *,
    deconstruct: Annotated[
        bool,
        typer.Option(
            "--deconstruct",
            "-d",
            help=(
                "Deconstruct built integrations or playbooks instead of building them."
                " Does work only with --integration."
            ),
        ),
    ] = False,
    custom_integration: Annotated[
        bool,
        typer.Option(
            help="Build a single specific integration rather than the full custom repository.",
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
    """Run the `mp build` command.

    Args:
        repositories: the repositories to build
        integrations: the integrations to build
        playbooks: the playbooks to build
        src: Customize source folder to build from.
        dst: Customize destination folder to build to.
        deconstruct: whether to deconstruct instead of build
        custom_integration: if need to build specific integration from the custom repo.
        quiet: quiet log options
        verbose: Verbose log options

    """
    repositories = ensure_valid_list(repositories)
    integrations = ensure_valid_list(integrations)
    playbooks = ensure_valid_list(playbooks)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: BuildParams = BuildParams(
        repository=repositories,
        integrations=integrations,
        playbooks=playbooks,
        deconstruct=deconstruct,
        custom_integration=custom_integration,
        src=src,
        dst=dst,
    )
    params.validate()

    if should_preform_integration_logic(integrations, repositories):
        build_integrations(
            integrations,
            repositories,
            src=src,
            dst=dst,
            deconstruct=deconstruct,
            custom_integration=custom_integration,
        )

    if should_preform_playbook_logic(playbooks, repositories):
        build_playbooks(playbooks, repositories, src=src, dst=dst, deconstruct=deconstruct)
