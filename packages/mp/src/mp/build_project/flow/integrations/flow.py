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

from typing import TYPE_CHECKING

import rich

import mp.core.constants
import mp.core.file_utils
from mp.build_project.integrations_repo import IntegrationsRepo
from mp.build_project.post_build.integrations.duplicate_integrations import (
    raise_errors_for_duplicate_integrations,
)
from mp.core.custom_types import RepositoryType

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def should_build_integrations(
    integrations: Iterable[str],
    repos: Iterable[RepositoryType],
) -> bool:
    """Decide if needed to build integrations or not.

    Returns:
        True if yes overwise False

    """
    return integrations or RepositoryType.COMMERCIAL in repos or RepositoryType.COMMUNITY in repos


def build_integrations(
    integrations: Iterable[str],
    integration_groups: Iterable[str],
    repositories: Iterable[RepositoryType],
    *,
    deconstruct: bool = False,
) -> None:
    """Entry point of the build or deconstruct integration operation."""
    commercial_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMERCIAL)
    community_path: Path = mp.core.file_utils.get_integrations_path(RepositoryType.COMMUNITY)
    commercial_mp: IntegrationsRepo = IntegrationsRepo(commercial_path)
    community_mp: IntegrationsRepo = IntegrationsRepo(community_path)
    if integrations:
        rich.print("Building integrations...")
        commercial_not_found: set[str] = _build_integrations(
            set(integrations), commercial_mp, deconstruct=deconstruct
        )
        community_not_found: set[str] = _build_integrations(
            set(integrations), community_mp, deconstruct=deconstruct
        )
        if commercial_not_found.intersection(community_not_found):
            rich.print(mp.core.constants.RECONFIGURE_MP_MSG)

        rich.print("Done building integrations.")

    elif integration_groups:
        build_integration_groups(integration_groups, commercial_mp, community_mp)

    elif repositories:
        _build_integration_repositories(repositories, commercial_mp, community_mp)


def build_integration_groups(
    groups: Iterable[str],
    commercial_mp: IntegrationsRepo,
    community_mp: IntegrationsRepo,
) -> None:
    """Build integration according to their groups."""
    rich.print("Building integration groups...")
    _build_integration_groups(set(groups), commercial_mp)
    _build_integration_groups(set(groups), community_mp)
    rich.print("Done building integration groups.")


def _build_integration_groups(groups: Iterable[str], marketplace_: IntegrationsRepo) -> None:
    valid_groups: set[Path] = _get_marketplace_paths_from_names(groups, marketplace_.paths)
    valid_group_names: set[str] = {g.name for g in valid_groups}
    not_found: set[str] = set(groups).difference(valid_group_names)
    if not_found:
        rich.print(f"The following groups could not be found: {', '.join(not_found)}")

    if valid_groups:
        rich.print(f"Building the following groups: {', '.join(valid_group_names)}")
        marketplace_.build_groups(valid_groups)


def _build_integration_repositories(
    repositories: Iterable[RepositoryType],
    commercial_mp: IntegrationsRepo,
    community_mp: IntegrationsRepo,
) -> None:
    repos: set[RepositoryType] = set(repositories)
    if _is_commercial_repo(repos):
        rich.print("Building all integrations and groups in commercial repo...")
        commercial_mp.build()
        commercial_mp.write_marketplace_json()
        rich.print("Done Commercial integrations build.")

    if _is_community_repo(repos):
        rich.print("Building all integrations and groups in third party repo...")
        community_mp.build()
        community_mp.write_marketplace_json()
        rich.print("Done third party integrations build.")

    if _is_full_repo_build(repos):
        rich.print("Checking for duplicate integrations...")
        raise_errors_for_duplicate_integrations(
            commercial_path=commercial_mp.out_dir,
            community_path=commercial_mp.out_dir,
        )
        rich.print("Done checking for duplicate integrations.")


def _is_commercial_repo(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.COMMERCIAL in repos


def _is_community_repo(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.COMMUNITY in repos


def _is_full_repo_build(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.COMMERCIAL in repos and RepositoryType.COMMUNITY in repos


def _build_integrations(
    integrations: Iterable[str],
    marketplace_: IntegrationsRepo,
    *,
    deconstruct: bool,
) -> set[str]:
    valid_integrations_: set[Path] = _get_marketplace_paths_from_names(
        integrations,
        marketplace_.paths,
    )
    valid_integration_names: set[str] = {i.name for i in valid_integrations_}
    not_found: set[str] = set(integrations).difference(valid_integration_names)
    if not_found:
        rich.print(
            "The following integrations could not be found in"
            f" the {marketplace_.name} marketplace: {', '.join(not_found)}\n"
        )

    if valid_integrations_:
        rich.print(
            "[blue]Building the following integrations in the"
            f" the {marketplace_.name} marketplace:"
            f" {', '.join(valid_integration_names)}[/blue]"
        )
        if deconstruct:
            marketplace_.deconstruct_integrations(valid_integrations_)

        else:
            marketplace_.build_integrations(valid_integrations_)

    return not_found


def _get_marketplace_paths_from_names(
    names: Iterable[str],
    marketplace_paths: Iterable[Path],
) -> set[Path]:
    results: set[Path] = set()
    for path in marketplace_paths:
        results.update({p for n in names if (p := path / n).exists()})

    return results
