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

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import mp.core.config
import mp.core.file_utils
from mp.build_project.integrations_repo import IntegrationsRepo
from mp.core.custom_types import RepositoryType
from mp.validate.data_models import ContentType, FullReport, ValidationFn, ValidationResults
from mp.validate.utils import combine_results, get_marketplace_paths_from_names, should_fail_program
from mp.validate.validations import Validations

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


def validate_integrations(
    integrations: Iterable[str],
    repositories: Iterable[RepositoryType],
) -> tuple[FullReport, bool]:
    """Run validations on a list of integrations or on all of them.

    Args:
        integrations: An iterable of playbook names to validate.
        repositories: An iterable of repository to validate.

    Returns:
        Both the Report and the fail status of the validations.

    """
    commercial_path: Path = mp.core.file_utils.get_integrations_repo_base_path(RepositoryType.COMMERCIAL)
    community_path: Path = mp.core.file_utils.get_integrations_repo_base_path(RepositoryType.THIRD_PARTY)
    commercial_mp: IntegrationsRepo = IntegrationsRepo(commercial_path)
    community_mp: IntegrationsRepo = IntegrationsRepo(community_path)

    commercial_output: FullReport
    community_output: FullReport

    if integrations:
        commercial_output = _validate_integrations(
            get_marketplace_paths_from_names(integrations, commercial_mp.paths),
        )

        community_output = _validate_integrations(
            get_marketplace_paths_from_names(integrations, community_mp.paths),
        )

    else:
        repos: set[RepositoryType] = set(repositories)
        commercial_output = {}
        community_output = {}
        if RepositoryType.ALL_CONTENT in repos or RepositoryType.COMMERCIAL in repos:
            commercial_output = _validate_repo(commercial_mp)

        if RepositoryType.ALL_CONTENT in repos or RepositoryType.THIRD_PARTY in repos:
            community_output = _validate_repo(community_mp)

    validations_output: FullReport = combine_results(commercial_output, community_output)

    should_fail: bool = should_fail_program(validations_output)
    return validations_output, should_fail


def _validate_repo(marketplace: IntegrationsRepo) -> FullReport:
    integrations: set[Path] = mp.core.file_utils.get_integrations_from_paths(*marketplace.paths)

    return _validate_integrations(integrations)


def _validate_integrations(
    integrations: Iterable[Path],
) -> FullReport:
    """Validate a list of integration names within a specific marketplace scope.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    validation_outputs: FullReport = {}
    if not integrations:
        return validation_outputs

    validation_output: list[ValidationResults] = _run_validations(integrations, _run_validation)
    validation_outputs["Validations"] = validation_output

    return validation_outputs


def _run_validations(integration: Iterable[Path], validation_function: ValidationFn) -> list[ValidationResults]:
    """Execute validation checks on a list of integration paths.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    paths: Iterator[Path] = (i for i in integration if i.exists() and mp.core.file_utils.is_integration(i))

    processes: int = mp.core.config.get_processes_number()
    with ThreadPoolExecutor(max_workers=processes) as pool:
        results = pool.map(validation_function, paths)
        validation_outputs: list[ValidationResults] = list(results)

    return validation_outputs


def _run_validation(integration_path: Path) -> ValidationResults:
    validation_object: Validations = Validations(integration_path, ContentType.INTEGRATION)
    validation_object.run_validation()
    return validation_object.results
