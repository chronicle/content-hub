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
from mp.build_project.playbooks_repo import PlaybooksRepo
from mp.core.custom_types import RepositoryType
from mp.validate.data_models import (
    PRE_BUILD,
    Configurations,
    ContentType,
    FullReport,
    ValidationFn,
    ValidationResults,
)
from mp.validate.pre_build_validation import PreBuildValidations
from mp.validate.utils import combine_results, should_fail_program

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def validate_playbooks(
    playbooks: Iterable[str],
    repositories: Iterable[RepositoryType],
    *,
    only_pre_build: bool = False,
) -> tuple[FullReport, bool]:
    """Run validations on a list of playbook or on all of them.

    Args:
        playbooks: An iterable of playbook names to validate.
        repositories: An iterable of repository to validate.
        only_pre_build: If True, only pre-build validations will run.

    Returns:
        Both the Report and the fail status of the validations.

    """
    commercial_playbooks_repo: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_playbook_repository_base_path(RepositoryType.COMMERCIAL.value)
    )
    community_playbooks_repo: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_playbook_repository_base_path(RepositoryType.COMMUNITY.value)
    )

    run_configurations: Configurations = Configurations(only_pre_build=only_pre_build)

    commercial_output: FullReport = {}
    community_output: FullReport = {}

    if playbooks:
        commercial_output = _validate_playbooks(
            playbooks, commercial_playbooks_repo, run_configurations
        )
        community_output = _validate_playbooks(
            playbooks, community_playbooks_repo, run_configurations
        )

    elif repositories:
        commercial_output = _validate_repo(commercial_playbooks_repo, run_configurations)
        community_output = _validate_repo(community_playbooks_repo, run_configurations)

    validations_output: FullReport = combine_results(commercial_output, community_output)

    should_fail: bool = should_fail_program(validations_output)
    return validations_output, should_fail


def _validate_repo(playbook_repo: PlaybooksRepo, run_configurations: Configurations) -> FullReport:
    all_playbooks_in_repo: Iterable[str] = [
        n.name for n in playbook_repo.repository_base_path.iterdir()
    ]
    return _validate_playbooks(all_playbooks_in_repo, playbook_repo, run_configurations)


def _validate_playbooks(
    playbooks_names: Iterable[str],
    content_repo: PlaybooksRepo,
    configurations: Configurations,
) -> FullReport:
    validation_outputs: FullReport = {}
    playbooks_paths: Iterable[Path] = _get_playbooks_paths_from_repository(
        playbooks_names, content_repo.repository_base_path
    )

    if not playbooks_paths:
        return validation_outputs

    pre_build_output: list[ValidationResults] = _run_validations(
        playbooks_paths, _run_pre_build_validations
    )
    validation_outputs[PRE_BUILD] = pre_build_output

    if not configurations.only_pre_build:
        content_repo.build_playbooks(playbooks_paths)

    return validation_outputs


def _run_validations(
    playbooks: Iterable[Path], validation_function: ValidationFn
) -> list[ValidationResults]:
    """Execute pre-build validation checks on a list of playbook paths.

    Returns:
        list[ValidationResults]: List contains the Validation results object

    """
    processes: int = mp.core.config.get_processes_number()
    with multiprocessing.Pool(processes=processes) as pool:
        results = pool.imap_unordered(validation_function, playbooks)
        validation_outputs: list[ValidationResults] = [r for r in results if not r.is_success]

    return validation_outputs


def _run_pre_build_validations(playbook_path: Path) -> ValidationResults:
    validation_object: PreBuildValidations = PreBuildValidations(
        playbook_path, ContentType.PLAYBOOK
    )
    validation_object.run_pre_build_validation()
    return validation_object.results


def _get_playbooks_paths_from_repository(
    playbooks_names: Iterable[str], repository_path: Path
) -> set[Path]:
    return {
        p
        for n in playbooks_names
        if (p := repository_path / n).exists() and mp.core.file_utils.is_non_built_playbook(p)
    }
