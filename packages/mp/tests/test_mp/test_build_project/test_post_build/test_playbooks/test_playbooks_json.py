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

import shutil
from typing import TYPE_CHECKING

from deepdiff import DeepDiff

import mp.build_project.post_build.playbooks.playbooks_json
import mp.core.constants
import test_mp.common
from mp.build_project.playbooks_repo import Playbooks

if TYPE_CHECKING:
    from pathlib import Path

NO_DIFF: dict = {}


def test_write_playbooks_json(
    tmp_path: Path,
    built_playbook_path: Path,
    non_built_playbook_path: Path,
    playbooks_json_path: Path
) -> None:
    commercial: Path = tmp_path / mp.core.constants.COMMERCIAL_DIR_NAME
    commercial_playbooks = Playbooks(commercial)
    commercial_playbooks.repository_base_path.mkdir(parents=True, exist_ok=True)
    commercial_playbooks.out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(built_playbook_path, commercial_playbooks.out_dir / "mock_non_built_playbook.json")
    shutil.copytree(
        non_built_playbook_path,
        commercial_playbooks.repository_base_path / non_built_playbook_path.name,
    )

    community: Path = tmp_path / mp.core.constants.COMMUNITY_DIR_NAME
    community_playbooks = Playbooks(community)
    community_playbooks.repository_base_path.mkdir(parents=True, exist_ok=True)
    community_playbooks.out_dir.mkdir(parents=True, exist_ok=True)

    mp.build_project.post_build.playbooks.playbooks_json.write_playbooks_json(
        commercial_playbooks, community_playbooks
    )

    out_playbooks_json_path = (
        commercial_playbooks.out_dir.parent / mp.core.constants.PLAYBOOKS_JSON_NAME
    )
    expected, actual = test_mp.common.get_json_content(
        expected=playbooks_json_path, actual=out_playbooks_json_path
    )
    assert DeepDiff(expected, actual, ignore_order=True) == NO_DIFF
