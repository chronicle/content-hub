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
from mp.core.utils import (
    ensure_valid_list,
)
from mp.telemetry import track_command
from mp.validate.data_models import ContentType, FullReport
from mp.validate.display import display_validation_reports
from mp.validate.flow.playbooks.flow import validate_playbooks

if TYPE_CHECKING:
    from mp.core.config import RuntimeParams

app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class ValidateParams:
    playbooks: list[str]

    def validate(self) -> None:
        """Validate the parameters.

        Validates the provided parameters
        to ensure proper usage of mutually exclusive
        options and constraints.

        Raises:
            typer.BadParameter:
                If the parameter is not used correctly.

        """
        msg: str

        if len(self.playbooks) == 0:
            msg = "At least one playbook must be provided to run this action."
            raise typer.BadParameter(msg)


@app.command(name="playbook", help="Validate the content-hub playbooks")
@app.command(name="p", help="Validate the content-hub playbooks")
@track_command
def validate_playbook(  # noqa: PLR0913
    playbooks: Annotated[
        list[str],
        typer.Argument(
            help="Playbooks to validate.",
            default_factory=list,
        ),
    ],
    *,
    only_pre_build: Annotated[
        bool,
        typer.Option(
            help=(
                "Execute only pre-build validations "
                "checks on the playbooks, skipping the full build process."
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

    Validate playbooks within the marketplace based on specified criteria.

    Args:
        playbooks: A list of specific playbooks to validate.
        only_pre_build: If set to True, only pre-build validation checks are
                        performed.
        quiet: quiet log options
        verbose: Verbose log options

    Raises:
        typer.Exit: If validation fails, the program will exit with code 1.

    """
    playbooks = ensure_valid_list(playbooks)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: ValidateParams = ValidateParams(playbooks)
    params.validate()

    full_report: dict[ContentType, FullReport] = {}
    should_fail: bool = False

    if playbooks:
        full_report[ContentType.PLAYBOOK], should_fail = validate_playbooks(
            playbooks=playbooks, repositories=[], only_pre_build=only_pre_build
        )

    display_validation_reports(full_report)

    if should_fail:
        raise typer.Exit(1)
