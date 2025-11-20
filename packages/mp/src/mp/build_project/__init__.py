"""Package for building and deconstructing integration projects.

This package provides the `build` CLI command for processing integration
repositories, groups, or individual integrations. It handles both building
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
from typing import TYPE_CHECKING, Annotated

import typer

import mp.core.config
from mp.core.custom_types import RepositoryType  # noqa: TC001
from mp.core.utils import ensure_valid_list
from mp.telemetry import track_command

from .utils.integrations.utils import build_integrations, should_build_integrations
from .utils.playbooks.utils import should_build_playbooks, build_playbooks

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mp.core.config import RuntimeParams


__all__: list[str] = ["app", "build"]
app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class BuildParams:
    repository: Iterable[RepositoryType]
    integrations: Iterable[str]
    groups: Iterable[str]
    playbooks: Iterable[str]
    deconstruct: bool

    def validate(self) -> None:
        """Validate the parameters.

        Validates the provided parameters
        to ensure proper usage of mutually exclusive
        options and constraints.
        Handles error messages and raises exceptions if validation fails.

        Raises:
            typer.BadParameter:
                If none of the required options (--repository, --groups, or
                --integration) are provided.
            typer.BadParameter:
                If more than one of the options (--repository, --groups,
                or --integration) is used at the same time.
            typer.BadParameter:
                If the --deconstruct option is used with any option
                other than --integration.

        """
        params: list[Iterable[str] | Iterable[RepositoryType]] = self._as_list()
        msg: str
        if not any(params):
            msg = "At least one of --repository, --groups, --integration, --playbook must be used."
            raise typer.BadParameter(msg)

        if sum(map(bool, params)) != 1:
            msg = "Only one of --repository, --groups, --integration, --playbook shall be used."
            raise typer.BadParameter(msg)

        if self.deconstruct and (self.groups or self.repository):
            msg = "--deconstruct works only with --integration or --playbook."
            raise typer.BadParameter(msg)

    def _as_list(self) -> list[Iterable[RepositoryType] | Iterable[str]]:
        return [self.repository, self.integrations, self.groups]


@app.command(name="build", help="Build the marketplace")
@track_command
def build(  # noqa: PLR0913
    repository: Annotated[
        list[RepositoryType],
        typer.Option(
            help="Build all integrations in specified integration repositories",
            default_factory=list,
        ),
    ],
    integration: Annotated[
        list[str],
        typer.Option(
            help="Build a specified integration",
            default_factory=list,
        ),
    ],
    integration_group: Annotated[
        list[str],
        typer.Option(
            help="Build all integrations of a specified integration group",
            default_factory=list,
        ),
    ],
    playbook: Annotated[
        list[str],
        typer.Option(
            help="Build a specified playbook",
            default_factory=list,
        ),
    ],
    *,
    deconstruct: Annotated[
        bool,
        typer.Option(
            help=(
                "Deconstruct built integrations instead of building them."
                " Does work only with --integration."
            ),
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            help="Log less on runtime.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            help="Log more on runtime.",
        ),
    ] = False,
) -> None:
    """Run the `mp build` command.

    Args:
        repository: the repository to build
        integration: the integrations to build
        integration_group: the integration groups to build
        playbook: the playbooks to build
        deconstruct: whether to deconstruct instead of build
        quiet: quiet log options
        verbose: Verbose log options

    """
    repository = ensure_valid_list(repository)
    integration = ensure_valid_list(integration)
    integration_group = ensure_valid_list(integration_group)
    playbook = ensure_valid_list(playbook)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: BuildParams = BuildParams(
        repository=repository,
        integrations=integration,
        groups=integration_group,
        playbooks=playbook,
        deconstruct=deconstruct,
    )
    params.validate()

    if should_build_integrations(integration, repository):
        build_integrations(integration, integration_group, repository, deconstruct=deconstruct)

    if should_build_playbooks(playbook, repository):
        build_playbooks(playbook, repository, deconstruct=deconstruct)
