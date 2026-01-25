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
from mp.build_project.playbooks_repo import PlaybooksRepo
from mp.build_project.post_build.playbooks.playbooks_json import write_playbooks_json

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.custom_types import RepositoryType


class Repos(NamedTuple):
    commercial: PlaybooksRepo
    community: PlaybooksRepo
    custom: PlaybooksRepo | None = None


def build_playbooks(
    playbooks: Iterable[str],
    repositories: Iterable[RepositoryType],
    src: Path | None,
    dst: Path | None,
    *,
    deconstruct: bool = False,
) -> None:
    """Entry point of the build or deconstruct playbook operation."""
    repos: Repos = _create_repos(src, dst)

    if playbooks:
        if repos.custom is not None:
            _build_playbooks(set(playbooks), repos.custom, deconstruct=deconstruct)

        else:
            commercial_not_found: set[str] = _build_playbooks(
                set(playbooks), repos.commercial, deconstruct=deconstruct
            )
            community_not_found: set[str] = _build_playbooks(
                set(playbooks), repos.community, deconstruct=deconstruct
            )

            if commercial_not_found.intersection(community_not_found):
                rich.print(mp.core.constants.RECONFIGURE_MP_MSG)

    elif repositories:
        _build_playbooks_repositories([repos.commercial, repos.community])
        write_playbooks_json(repos.commercial, repos.community)


def _create_repos(modified_src: Path | None, modified_dst: Path | None) -> Repos:
    commercial: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_or_create_playbook_repo_base_path(
            mp.core.constants.COMMERCIAL_REPO_NAME,
        ),
        dst=modified_dst,
    )
    community: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_or_create_playbook_repo_base_path(
            mp.core.constants.THIRD_PARTY_REPO_NAME,
        ),
        dst=modified_dst,
    )
    custom: PlaybooksRepo | None = None
    if modified_src and modified_dst:
        custom: PlaybooksRepo = PlaybooksRepo(modified_src, modified_dst, default_src=False)
    elif modified_src:
        custom: PlaybooksRepo = PlaybooksRepo(modified_src, default_src=False)

    return Repos(commercial, community, custom)


def _build_playbooks_repositories(repos: list[PlaybooksRepo]) -> None:
    rich.print("[blue]Building all playbooks in repository...[/blue]")
    for repository in repos:
        _build_single_repo_folder(repository)
    rich.print("[blue]Done repository playbook build.[/blue]")


def _build_single_repo_folder(repository: PlaybooksRepo) -> None:
    for folder in repository.base_folders:
        try:
            playbooks_paths: list[Path] = list(folder.iterdir())
            repository.build_playbooks(playbooks_paths)
        except FileNotFoundError:
            continue


def _build_playbooks(
    playbooks: Iterable[str],
    repository: PlaybooksRepo,
    *,
    deconstruct: bool,
) -> set[str]:
    valid_playbooks_paths: set[Path] = _get_playbooks_paths_from_repository(
        playbooks, repository.base_folders, deconstruct=deconstruct
    )
    valid_playbooks_names: set[str] = {i.name for i in valid_playbooks_paths}
    normalized_playbooks: set[str] = {
        _normalize_name_to_json(name, deconstruct=deconstruct) for name in playbooks
    }
    not_found_playbooks: set[str] = normalized_playbooks.difference(valid_playbooks_names)
    if not_found_playbooks:
        rich.print(
            f"The following playbooks could not be found in the {repository.name} "
            f"repository: {', '.join(not_found_playbooks)}"
        )

    if valid_playbooks_paths:
        rich.print(
            f"[blue]Building the following playbooks: {', '.join(valid_playbooks_names)}[/blue]"
        )

        if deconstruct:
            repository.deconstruct_playbooks(valid_playbooks_paths)
        else:
            repository.build_playbooks(valid_playbooks_paths)

    return not_found_playbooks


def _get_playbooks_paths_from_repository(
    playbooks_names: Iterable[str], repositories_paths: list[Path], *, deconstruct: bool = False
) -> set[Path]:
    result: set[Path] = set()
    normalized_names = [
        _normalize_name_to_json(n, deconstruct=deconstruct) for n in playbooks_names
    ]
    for path in repositories_paths:
        result.update(p for n in normalized_names if (p := path / n).exists())
    return result


def _normalize_name_to_json(name: str, *, deconstruct: bool = False) -> str:
    if deconstruct and not name.endswith(mp.core.constants.JSON_SUFFIX):
        name = f"{name}{mp.core.constants.JSON_SUFFIX}"
    return name
