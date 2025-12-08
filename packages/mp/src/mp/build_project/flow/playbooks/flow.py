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
from mp.build_project.playbooks_repo import PlaybooksRepo
from mp.build_project.post_build.playbooks.playbooks_json import write_playbooks_json

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from mp.core.custom_types import RepositoryType


def build_playbooks(
    playbooks: Iterable[str],
    repositories: Iterable[RepositoryType],
    *,
    deconstruct: bool = False,
) -> None:
    """Entry point of the build or deconstruct playbook operation."""
    commercial_playbooks: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_playbook_repository_base_path(mp.core.constants.COMMERCIAL_DIR_NAME)
    )
    community_playbooks: PlaybooksRepo = PlaybooksRepo(
        mp.core.file_utils.get_playbook_repository_base_path(mp.core.constants.COMMUNITY_DIR_NAME)
    )

    if playbooks:
        commercial_not_found: set[str] = _build_playbooks(
            set(playbooks), commercial_playbooks, deconstruct=deconstruct
        )
        community_not_found: set[str] = _build_playbooks(
            set(playbooks), community_playbooks, deconstruct=deconstruct
        )

        if commercial_not_found.intersection(community_not_found):
            rich.print(mp.core.constants.RECONFIGURE_MP_MSG)

    elif repositories:
        _build_playbooks_repositories(commercial_playbooks, community_playbooks)
        write_playbooks_json(commercial_playbooks, community_playbooks)


def _build_playbooks_repositories(
    commercial_playbooks: PlaybooksRepo,
    community_playbooks: PlaybooksRepo,
) -> None:
    rich.print("[blue]Building all playbooks in repository...[/blue]")
    commercial_playbooks.build_playbooks(commercial_playbooks.repository_base_path.iterdir())
    community_playbooks.build_playbooks(community_playbooks.repository_base_path.iterdir())
    rich.print("[blue]Done repository playbook build.[/blue]")


def _build_playbooks(
    playbooks: Iterable[str],
    repository: PlaybooksRepo,
    *,
    deconstruct: bool,
) -> set[str]:
    valid_playbooks_paths: set[Path] = _get_playbooks_paths_from_repository(
        playbooks, repository.repository_base_path, deconstruct=deconstruct
    )
    valid_playbooks_names: set[str] = {i.name for i in valid_playbooks_paths}
    normalized_playbooks: set[str] = {
        _normalize_name_to_json(name, deconstruct=deconstruct) for name in playbooks
    }
    not_found_playbooks: set[str] = normalized_playbooks.difference(valid_playbooks_names)
    if not_found_playbooks:
        rich.print(
            f"The following playbooks could not be found in the {repository.repository_name} "
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
    playbooks_names: Iterable[str], repository_path: Path, *, deconstruct: bool = False
) -> set[Path]:
    normalized_names = (
        _normalize_name_to_json(n, deconstruct=deconstruct) for n in playbooks_names
    )
    return {p for n in normalized_names if (p := repository_path / n).exists()}


def _normalize_name_to_json(name: str, *, deconstruct: bool = False) -> str:
    if deconstruct and not name.endswith(mp.core.constants.WIDGETS_META_SUFFIX):
        name = f"{name}{mp.core.constants.WIDGETS_META_SUFFIX}"
    return name
