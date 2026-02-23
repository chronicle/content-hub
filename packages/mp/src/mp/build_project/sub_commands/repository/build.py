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
from mp.build_project.flow.integrations.flow import build_integrations
from mp.build_project.flow.playbooks.flow import build_playbooks
from mp.core.custom_types import RepositoryType  # noqa: TC001
from mp.core.utils import ensure_valid_list
from mp.core.utils.common import is_integration_repo, is_playbook_repo
from mp.telemetry import track_command

if TYPE_CHECKING:
    from mp.core.config import RuntimeParams

app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class BuildParams:
    repositories: list[RepositoryType]

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

        if len(self.repositories) == 0:
            msg = "At least one repository type need to be used: google, third_party or playbooks."
            raise typer.BadParameter(msg)


@app.command(name="repository", help="Build content-hub full repository.")
@track_command
def build_repository(
    repositories: Annotated[
        list[RepositoryType],
        typer.Argument(
            help="'google' - for commercial integrations, 'third_party' - for community and partner"
            " integrations, custom - for custom integrations, 'playbooks' for playbooks.",
        ),
    ],
    *,
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
        quiet: quiet log options
        verbose: Verbose log options

    """
    repositories = ensure_valid_list(repositories)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: BuildParams = BuildParams(repositories=repositories)
    params.validate()

    if is_integration_repo(repositories):
        build_integrations(
            integrations=[],
            repositories=repositories,
            src=None,
            dst=None,
            deconstruct=False,
            custom_integration=False,
        )

    if is_playbook_repo(repositories):
        build_playbooks(
            playbooks=[], repositories=repositories, src=None, dst=None, deconstruct=False
        )
