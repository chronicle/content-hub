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
from mp.core.custom_types import RepositoryType
from mp.core.utils import (
    ensure_valid_list,
)
from mp.telemetry import track_command
from mp.validate.data_models import ContentType, FullReport
from mp.validate.display import display_validation_reports
from mp.validate.flow.integrations.flow import validate_integrations
from mp.validate.flow.playbooks.flow import validate_playbooks

if TYPE_CHECKING:
    from mp.core.config import RuntimeParams

app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class ValidateParams:
    repositories: list[RepositoryType]

    def validate(self) -> None:
        """Validate the parameters.

        Validates the provided parameters
        to ensure proper usage of mutually exclusive
        options and constraints.
        Handles error messages and raises exceptions if validation fails.

        Raises:
            typer.BadParameter:
                If none of the required options (--repository or
                --integration) are provided.
            typer.BadParameter:
                If more than one of the options (--repository,
                or --integration) is used at the same time.

        """
        msg: str

        if len(self.repositories) == 0:
            msg = "At least one repository type need to be used: google, third_party or playbooks."
            raise typer.BadParameter(msg)


@app.command(name="repository", help="Validate content-hub full repository.")
@app.command(name="r", help="Validate content-hub full repository.")
@track_command
def validate_repository(
    repositories: Annotated[
        list[RepositoryType],
        typer.Argument(
            help="'google' - for commercial integrations, 'third_party' - for community and partner"
            " integrations, 'playbooks' for playbooks.",
        ),
    ],
    *,
    only_pre_build: Annotated[
        bool,
        typer.Option(
            help=(
                "Execute only pre-build validations "
                "checks on the integrations, skipping the full build process."
            ),
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress most logging output during runtime, showing only essential information.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging output during runtime for detailed debugging information.",
        ),
    ] = False,
) -> None:
    """Run the mp validate command.

    Validate repositories within the content-hub based on specified criteria.

    Args:
        repositories: repository type on which to run validation.
                    Validation will be performed on all content found
                    within this repository.
        only_pre_build: If set to True, only pre-build validation checks are
                        performed.
        quiet: quiet log options
        verbose: Verbose log options

    Raises:
        typer.Exit: If validation fails, the program will exit with code 1.

    """
    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    repositories = ensure_valid_list(repositories)
    params: ValidateParams = ValidateParams(repositories)
    params.validate()

    full_report: dict[ContentType, FullReport] = {}
    f1, f2 = False, False
    if _is_integration_repo(repositories):
        full_report[ContentType.INTEGRATION], f1 = validate_integrations(
            integrations=[], repositories=repositories, only_pre_build=only_pre_build
        )

    if _is_playbook_repo(repositories):
        full_report[ContentType.PLAYBOOK], f2 = validate_playbooks(
            playbooks=[], repositories=repositories, only_pre_build=only_pre_build
        )

    display_validation_reports(full_report)

    if f1 or f2:
        raise typer.Exit(1)


def _is_integration_repo(repositories: list[RepositoryType]) -> bool:
    return (
        RepositoryType.ALL_CONTENT in repositories
        or RepositoryType.COMMERCIAL in repositories
        or RepositoryType.THIRD_PARTY in repositories
        or RepositoryType.CUSTOM in repositories
    )


def _is_playbook_repo(repositories: list[RepositoryType]) -> bool:
    return RepositoryType.ALL_CONTENT in repositories or RepositoryType.PLAYBOOKS in repositories
