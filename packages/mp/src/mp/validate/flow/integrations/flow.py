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

import multiprocessing
from typing import TYPE_CHECKING

import mp.core.config
import mp.core.file_utils
from mp.build_project.integrations_repo import IntegrationsRepo
from mp.core.custom_types import Products, RepositoryType
from mp.validate.data_models import (
    PRE_BUILD,
    Configurations,
    ContentType,
    FullReport,
    ValidationFn,
    ValidationResults,
)
from mp.validate.pre_build_validation import PreBuildValidations
from mp.validate.utils import (
    combine_results,
    get_marketplace_paths_from_names,
    should_fail_program,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


def validate_integrations(
    integrations: Iterable[str],
    groups: Iterable[str],
    repositories: Iterable[RepositoryType],
    *,
    only_pre_build: bool = False,
) -> tuple[FullReport, bool]:
    """Run validations on a list of integrations or on all of them.

    Args:
        integrations: An iterable of playbook names to validate.
        groups: A list of integration groups.
        repositories: An iterable of repository to validate.
        only_pre_build: If True, only pre-build validations will run.

    Returns:
        Both the Report and the fail status of the validations.

    """
    commercial_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMERCIAL)
    community_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMUNITY)
    commercial_mp: IntegrationsRepo = IntegrationsRepo(commercial_path)
    community_mp: IntegrationsRepo = IntegrationsRepo(community_path)

    run_configurations: Configurations = Configurations(only_pre_build=only_pre_build)

    commercial_output: FullReport
    community_output: FullReport

    if integrations:
        commercial_output = _validate_integrations(
            get_marketplace_paths_from_names(integrations, commercial_mp.paths),
            commercial_mp,
            run_configurations,
        )

        community_output = _validate_integrations(
            get_marketplace_paths_from_names(integrations, community_mp.paths),
            community_mp,
            run_configurations,
        )

    elif groups:
        commercial_output = _validate_groups(
            get_marketplace_paths_from_names(groups, commercial_mp.paths),
            commercial_mp,
            run_configurations,
        )

        community_output = _validate_groups(
            get_marketplace_paths_from_names(groups, community_mp.paths),
            community_mp,
            run_configurations,
        )

    else:
        repos: set[RepositoryType] = set(repositories)
        commercial_output = {}
        community_output = {}
        if RepositoryType.COMMERCIAL in repos:
            commercial_output = _validate_repo(commercial_mp, run_configurations)

        if RepositoryType.COMMUNITY in repos:
            community_output = _validate_repo(community_mp, run_configurations)

    validations_output: FullReport = combine_results(commercial_output, community_output)

    should_fail: bool = should_fail_program(validations_output)
    return validations_output, should_fail


def _validate_repo(marketplace: IntegrationsRepo, configurations: Configurations) -> FullReport:
    products: Products[set[Path]] = mp.core.file_utils.get_integrations_and_groups_from_paths(
        *marketplace.paths
    )

    integrations_outputs: FullReport = _validate_integrations(
        products.integrations, marketplace, configurations
    )
    groups_output: FullReport = _validate_groups(products.groups, marketplace, configurations)

    validation_outputs: FullReport = combine_results(integrations_outputs, groups_output)

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
    if not groups:
        return validation_outputs

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
    validation_object: PreBuildValidations = PreBuildValidations(
        integration_path, ContentType.INTEGRATION
    )
    validation_object.run_pre_build_validation()
    return validation_object.results
