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
import multiprocessing
import pathlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, TypeAlias

import typer

import mp.core.config
import mp.core.file_utils
from mp.build_project.integrations_repo import IntegrationsRepo
from mp.core.custom_types import RepositoryType
from mp.core.utils import ensure_valid_list
from mp.telemetry import track_command

from .data_models import FullReport, ValidationResults
from .display import display_validation_reports
from .pre_build_validation.integrations import PreBuildValidations
from .utils import Configurations, get_marketplace_paths_from_names

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from mp.core.config import RuntimeParams
    from mp.core.custom_types import Products

PRE_BUILD: str = "Pre-Build"
BUILD: str = "Build"
POST_BUILD: str = "Post-Build"

ValidationFn: TypeAlias = Callable[[pathlib.Path], ValidationResults]


__all__: list[str] = ["Configurations", "app", "validate"]
app: typer.Typer = typer.Typer()


@dataclasses.dataclass(slots=True, frozen=True)
class ValidateParams:
    repository: Iterable[RepositoryType]
    integrations: Iterable[str]
    groups: Iterable[str]

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

        """
        mutually_exclusive_options = [self.repository, self.integrations, self.groups]
        msg: str

        if not any(mutually_exclusive_options):
            msg = "At least one of --repository, --groups, or --integration must be used."
            raise typer.BadParameter(msg)

        if sum(map(bool, mutually_exclusive_options)) != 1:
            msg = "Only one of --repository, --groups, or --integration shall be used."
            raise typer.BadParameter(msg)


@app.command(help="Validate the marketplace")
@track_command
def validate(  # noqa: PLR0913
    repository: Annotated[
        list[RepositoryType],
        typer.Option(
            help="Run validations on all integrations in specified integration repositories",
            default_factory=list,
        ),
    ],
    integration: Annotated[
        list[str],
        typer.Option(
            help="Run validations on a specified integrations.",
            default_factory=list,
        ),
    ],
    group: Annotated[
        list[str],
        typer.Option(
            help="Run validations on all integrations belonging to a specified integration group.",
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
            help="Suppress most logging output during runtime, showing only essential information.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            help="Enable verbose logging output during runtime for detailed debugging information.",
        ),
    ] = False,
) -> None:
    """Run the mp validate command.

    Validate integrations within the marketplace based on specified criteria.

    Args:
        repository: A list of repository types on which to run validation.
                    Validation will be performed on all integrations found
                    within these repositories.
        integration: A list of specific integration to validate.
        group: A list of integration groups. Validation will apply to all
               integrations associated with these groups.
        only_pre_build: If set to True, only pre-build validation checks are
                        performed.
        quiet: quiet log options
        verbose: Verbose log options

    Raises:
            typer.Exit: If one of the validations during the run failed

    """
    repository = ensure_valid_list(repository)
    integration = ensure_valid_list(integration)
    group = ensure_valid_list(group)

    run_params: RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    params: ValidateParams = ValidateParams(repository, integration, group)
    params.validate()

    commercial_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMERCIAL)
    community_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMUNITY)
    commercial_mp: IntegrationsRepo = IntegrationsRepo(commercial_path)
    community_mp: IntegrationsRepo = IntegrationsRepo(community_path)

    run_configurations: Configurations = Configurations(only_pre_build=only_pre_build)

    validations_output: FullReport = {}
    commercial_output: FullReport = {}
    community_output: FullReport = {}

    if integration:
        commercial_output = _validate_integrations(
            get_marketplace_paths_from_names(integration, commercial_mp.paths),
            commercial_mp,
            run_configurations,
        )

        community_output = _validate_integrations(
            get_marketplace_paths_from_names(integration, community_mp.paths),
            community_mp,
            run_configurations,
        )

        validations_output = _combine_results(commercial_output, community_output)

    elif group:
        commercial_output = _validate_groups(
            get_marketplace_paths_from_names(group, commercial_mp.paths),
            commercial_mp,
            run_configurations,
        )

        community_output = _validate_groups(
            get_marketplace_paths_from_names(group, community_mp.paths),
            community_mp,
            run_configurations,
        )

        validations_output = _combine_results(commercial_output, community_output)

    elif repository:
        repos: set[RepositoryType] = set(repository)

        if RepositoryType.COMMERCIAL in repos:
            commercial_output = _validate_repo(commercial_mp, run_configurations)

        if RepositoryType.COMMUNITY in repos:
            community_output = _validate_repo(community_mp, run_configurations)

        validations_output = _combine_results(commercial_output, community_output)

    display_validation_reports(validations_output)
    if _should_fail_program(validations_output):
        raise typer.Exit(code=1)


def _validate_repo(marketplace: IntegrationsRepo, configurations: Configurations) -> FullReport:
    products: Products[set[Path]] = mp.core.file_utils.get_integrations_and_groups_from_paths(
        *marketplace.paths
    )

    validation_outputs: FullReport

    integrations_outputs: FullReport = _validate_integrations(
        products.integrations, marketplace, configurations
    )
    groups_output: FullReport = _validate_groups(products.groups, marketplace, configurations)

    validation_outputs = _combine_results(integrations_outputs, groups_output)

    return validation_outputs


def _validate_groups(
    groups: Iterable[Path],
    marketplace: IntegrationsRepo,
    configurations: Configurations,
) -> FullReport:
    """Validate a list of integration group names within a specific marketplace scope.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    validation_outputs: FullReport = {}
    if groups:
        pre_build_output: list[ValidationResults] = _process_groups_for_validation(
            groups, _run_pre_build_validations
        )
        validation_outputs[PRE_BUILD] = pre_build_output

        if not configurations.only_pre_build:
            marketplace.build_groups(groups)

    return validation_outputs


def _process_groups_for_validation(
    groups: Iterable[Path],
    validation_function: ValidationFn,
) -> list[ValidationResults]:
    """Iterate through groups and perform pre-build validation on their integrations.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    validation_outputs: list[ValidationResults] = []
    for group_dir in groups:
        if group_dir.is_dir() and group_dir.exists():
            group_output: list[ValidationResults] = _run_validations(
                group_dir.iterdir(), validation_function
            )
            validation_outputs.extend(group_output)

    return validation_outputs


def _validate_integrations(
    integrations: Iterable[Path],
    marketplace: IntegrationsRepo,
    configurations: Configurations,
) -> FullReport:
    """Validate a list of integration names within a specific marketplace scope.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    validation_outputs: FullReport = {}
    if not integrations:
        return validation_outputs

    pre_build_output: list[ValidationResults] = _run_validations(
        integrations, _run_pre_build_validations
    )
    validation_outputs[PRE_BUILD] = pre_build_output

    if not configurations.only_pre_build:
        marketplace.build_integrations(integrations)

    return validation_outputs


def _run_validations(
    integration: Iterable[Path], validation_function: ValidationFn
) -> list[ValidationResults]:
    """Execute pre-build validation checks on a list of integration paths.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    paths: Iterator[Path] = (
        i for i in integration if i.exists() and mp.core.file_utils.is_integration(i)
    )

    processes: int = mp.core.config.get_processes_number()
    with multiprocessing.Pool(processes=processes) as pool:
        results = pool.imap_unordered(validation_function, paths)
        validation_outputs: list[ValidationResults] = [r for r in results if not r.is_success]

    return validation_outputs


def _run_pre_build_validations(integration_path: Path) -> ValidationResults:
    validation_object: PreBuildValidations = PreBuildValidations(integration_path)
    validation_object.run_pre_build_validation()
    return validation_object.results


def _combine_results(*validations_outputs: FullReport) -> FullReport:
    combined_output: FullReport = {}
    keys_to_combine = [PRE_BUILD, BUILD, POST_BUILD]

    for key in keys_to_combine:
        combined_list: list[ValidationResults] = []
        all_lists_are_none = True

        for output_dict in validations_outputs:
            current_list = output_dict.get(key)
            if current_list is not None:
                combined_list.extend(current_list)
                all_lists_are_none = False

        if all_lists_are_none:
            combined_output[key] = None
        else:
            combined_output[key] = combined_list

    return combined_output


def _should_fail_program(validations_output: FullReport) -> bool:
    return any(validation_result for validation_result in validations_output.values())
