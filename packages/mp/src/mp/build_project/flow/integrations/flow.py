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

from typing import TYPE_CHECKING, NamedTuple

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


class Repos(NamedTuple):
    commercial: IntegrationsRepo
    community: IntegrationsRepo
    custom: IntegrationsRepo


def build_integrations(
    integrations: Iterable[str],
    repositories: Iterable[RepositoryType],
    src: Path | None = None,
    *,
    deconstruct: bool = False,
    custom_integration: bool = False,
) -> None:
    """Entry point of the build or deconstruct integration operation."""
    repos = Repos(
        commercial=IntegrationsRepo(
            mp.core.file_utils.get_integrations_repo_base_path(RepositoryType.COMMERCIAL)
        ),
        community=IntegrationsRepo(
            mp.core.file_utils.get_integrations_repo_base_path(RepositoryType.THIRD_PARTY)
        ),
        custom=IntegrationsRepo(
            mp.core.file_utils.get_integrations_repo_base_path(RepositoryType.CUSTOM)
        )
        if not src
        else IntegrationsRepo(src, default_source=False),
    )

    if integrations:
        if custom_integration or src:
            not_founds = _build_integrations_from_repos(
                integrations,
                [repos.custom],
                deconstruct=deconstruct,
                start_msg="Building custom integrations...",
                end_msg="Done building custom integrations.",
            )
            if custom_not_found := not_founds[0]:
                rich.print(
                    "The following integrations could not be found in the custom repo: "
                    f"{', '.join(custom_not_found)}"
                )

        else:
            not_founds = _build_integrations_from_repos(
                integrations,
                [repos.commercial, repos.community],
                deconstruct=deconstruct,
                start_msg="Building integrations...",
                end_msg="Done building integrations.",
            )
            commercial_not_found, community_not_found = not_founds[0], not_founds[1]
            if commercial_not_found.intersection(community_not_found):
                rich.print(mp.core.constants.RECONFIGURE_MP_MSG)

    elif repositories:
        _build_integration_repositories(repositories, repos)


def _build_integration_repositories(
    repositories: Iterable[RepositoryType],
    repos: Repos,
) -> None:
    repo_types: set[RepositoryType] = set(repositories)
    if _is_commercial_repo(repo_types):
        rich.print("Building all integrations in commercial repo...")
        repos.commercial.build()
        repos.commercial.write_marketplace_json()
        rich.print("Done Commercial integrations build.")

    if _is_third_party_repo(repo_types):
        rich.print("Building all integrations in third party repo...")
        repos.community.build()
        repos.community.write_marketplace_json()
        rich.print("Done third party integrations build.")

    if _is_custom_repo(repo_types):
        rich.print("Building all integrations in custom repo...")
        repos.custom.build()
        rich.print("Done custom integrations build.")

    if _is_full_repo_build(repo_types):
        rich.print("Checking for duplicate integrations...")
        raise_errors_for_duplicate_integrations(
            commercial_path=repos.commercial.out_dir,
            community_path=repos.commercial.out_dir,
        )
        rich.print("Done checking for duplicate integrations.")


def _is_commercial_repo(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.COMMERCIAL in repos


def _is_third_party_repo(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.THIRD_PARTY in repos


def _is_full_repo_build(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.COMMERCIAL in repos and RepositoryType.THIRD_PARTY in repos


def _is_custom_repo(repos: Iterable[RepositoryType]) -> bool:
    return RepositoryType.CUSTOM in repos


def _build_integrations_from_repos(
    integrations: Iterable[str],
    repos: Iterable[IntegrationsRepo],
    *,
    deconstruct: bool,
    start_msg: str,
    end_msg: str,
) -> list[set[str]]:
    rich.print(start_msg)
    results = [
        _build_integrations(set(integrations), repo, deconstruct=deconstruct) for repo in repos
    ]
    rich.print(end_msg)
    return results


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
