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

import logging
import shutil
import unittest.mock
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from deepdiff import DeepDiff

import test_mp.common
from mp.build_project.playbooks_repo import PlaybooksRepo

if TYPE_CHECKING:
    from collections.abc import Callable

NO_DIFF: dict = {}

logger = logging.getLogger(__name__)


def test_build_non_built_playbook(
    tmp_path: Path,
    non_built_playbook_path: Path,
    mock_get_marketplace_path: str,
    assert_build_playbook: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_build_playbook(non_built_playbook_path)


def test_build_built_playbook(
    tmp_path: Path,
    built_playbook_path: Path,
    mock_get_marketplace_path: str,
    assert_build_playbook: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_build_playbook(built_playbook_path)


def test_non_existing_playbook_raises_file_not_found(
    tmp_path: Path, mock_get_marketplace_path: str, assert_build_playbook: Callable[[Path], None]
) -> None:
    with (
        unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path),
        pytest.raises(FileNotFoundError, match=r"Invalid playbook .*"),
    ):
        assert_build_playbook(Path(tmp_path / "non_existing_playbook"))


def test_save_values_while_deconstruct_and_build_playbook(
    tmp_path: Path, built_playbook_path: Path, mock_get_marketplace_path: str
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        mocked_repo: Path = tmp_path / built_playbook_path.parent.name
        shutil.copytree(built_playbook_path.parent, mocked_repo)
        playbook_to_deconstruct: Path = mocked_repo / built_playbook_path.name

        playbook_repo = PlaybooksRepo(mocked_repo)
        playbook_repo.deconstruct_playbook(playbook_to_deconstruct)
        deconstructed_playbook_path: Path = playbook_repo.out_dir / playbook_to_deconstruct.stem

        playbook_repo.build_playbook(deconstructed_playbook_path)
        rebuilt_playbook_path: Path = playbook_repo.out_dir / "mock_non_built_playbook.json"

        expected, actual = test_mp.common.get_json_content(
            expected=built_playbook_path, actual=rebuilt_playbook_path
        )

        assert DeepDiff(expected, actual, ignore_order=True) == NO_DIFF


@pytest.fixture
def assert_build_playbook(
    tmp_path: Path,
    built_playbook_path: Path,
) -> Callable[[Path], None]:
    def wrapper(playbook_path: Path) -> None:
        mocked_repo: Path = tmp_path / playbook_path.parent.name
        shutil.copytree(playbook_path.parent, mocked_repo)

        playbook_repo: PlaybooksRepo = PlaybooksRepo(mocked_repo)

        playbook: Path = mocked_repo / playbook_path.name
        playbook_repo.build_playbook(playbook)

        out_built_playbook: Path = playbook_repo.out_dir / Path(playbook_path.name + ".json")
        if not out_built_playbook.exists():
            out_built_playbook: Path = playbook_repo.out_dir / playbook_path.name

        expected, actual = test_mp.common.get_json_content(
            expected=built_playbook_path, actual=out_built_playbook
        )
        assert DeepDiff(expected, actual, ignore_order=True) == NO_DIFF

    return wrapper
