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

import rich
import typer

import mp.core.config
from mp.core.custom_types import RepositoryType
from mp.core.utils import (
    ensure_valid_list,
    should_preform_integration_logic,
    should_preform_playbook_logic,
)
from mp.telemetry import track_command
from mp.validate.data_models import ContentType, FullReport
from mp.validate.display import display_validation_reports
from mp.validate.flow.integrations.flow import validate_integrations
from mp.validate.flow.playbooks.flow import validate_playbooks

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mp.core.config import RuntimeParams


@dataclasses.dataclass(slots=True, frozen=True)
class ValidateParams:
    repository: Iterable[RepositoryType]
    integrations: Iterable[str]
    playbooks: Iterable[str]

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
        mutually_exclusive_options = [
            self.repository,
            self.integrations,
            self.playbooks,
        ]
        msg: str

        if not any(mutually_exclusive_options):
            msg = "At least one of --repository, or --integration must be used."
            raise typer.BadParameter(msg)

        if sum(map(bool, mutually_exclusive_options)) != 1:
            msg = "Only one of --repository, --integration or --playbooks shall be used."
            raise typer.BadParameter(msg)


@track_command
def validate(  # noqa: PLR0913
    ctx: typer.Context,
    repository: Annotated[
        list[RepositoryType],
        typer.Option(
            "--repository",
            "-r",
            help="Run validations on all integrations in specified integration repositories",
            default_factory=list,
        ),
    ],
    integration: Annotated[
        list[str],
        typer.Option(
            "--integration",
            "-i",
            help="Run validations on a specified integrations.",
            default_factory=list,
        ),
    ],
    playbook: Annotated[
        list[str],
        typer.Option(
            "--playbook",
            "-p",
            help="Build a specified playbook",
            default_factory=list,
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

    Validate integrations within the marketplace based on specified criteria.

    Args:
        ctx: typer context
        repository: A list of repository types on which to run validation.
                    Validation will be performed on all integrations found
                    within these repositories.
        integration: A list of specific integrations to validate.
        playbook: A list of specific playbooks to validate.
        only_pre_build: If set to True, only pre-build validation checks are
                        performed.
        quiet: quiet log options
        verbose: Verbose log options

    Raises:
        typer.Exit: If validation fails, the program will exit with code 1.

    """
    if ctx.invoked_subcommand is not None:
        return

    if not any([repository, integration, playbook]):
        typer.echo(ctx.get_help())
        raise typer.Exit

    rich.print(
        "[yellow]Note: 'validate' flags are deprecated. "
        "Use 'mp validate integration' or 'mp validate playbook' or mp validate repository "
        "instead.[/yellow]"
    )

    repositories = ensure_valid_list(repository)
    integrations = ensure_valid_list(integration)
    playbooks = ensure_valid_list(playbook)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: ValidateParams = ValidateParams(repositories, integrations, playbooks)
    params.validate()

    full_report: dict[ContentType, FullReport] = {}
    f1, f2 = False, False
    if RepositoryType.ALL_CONTENT in repositories or should_preform_integration_logic(
        integrations, repositories
    ):
        full_report[ContentType.INTEGRATION], f1 = validate_integrations(
            integrations, repositories, only_pre_build=only_pre_build
        )

    if RepositoryType.ALL_CONTENT in repositories or should_preform_playbook_logic(
        playbooks, repositories
    ):
        full_report[ContentType.PLAYBOOK], f2 = validate_playbooks(
            playbooks, repositories, only_pre_build=only_pre_build
        )

    display_validation_reports(full_report)

    if f1 or f2:
        raise typer.Exit(1)
