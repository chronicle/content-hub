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
import unittest.mock
from typing import TYPE_CHECKING

import pytest
from deepdiff import DeepDiff

import mp.core.constants
import test_mp.common
from mp.build_project.playbooks_repo import PlaybooksRepo

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

NO_DIFF: dict = {}


def test_deconstruct_built_playbook(
    tmp_path: Path,
    built_playbook_path: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_playbook: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_deconstruct_playbook(built_playbook_path)


def test_deconstruct_non_built_playbook(
    tmp_path: Path,
    non_built_playbook_path: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_playbook: Callable[[Path], None],
) -> None:
    with unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path):
        assert_deconstruct_playbook(non_built_playbook_path)


def test_non_existing_playbook_raises_file_not_found_error(
    tmp_path: Path,
    mock_get_marketplace_path: str,
    assert_deconstruct_playbook: Callable[[Path], None],
) -> None:
    with (
        unittest.mock.patch(mock_get_marketplace_path, return_value=tmp_path),
        pytest.raises(FileNotFoundError, match=r"Invalid playbook .*"),
    ):
        assert_deconstruct_playbook(tmp_path / "fake_playbook")


@pytest.fixture
def assert_deconstruct_playbook(
    tmp_path: Path,
    non_built_playbook_path: Path,
) -> Callable[[Path], None]:
    def compare_nested_files(expected_dir: Path, actual_dir: Path) -> None:
        expected_files: set[str] = {p.name for p in expected_dir.rglob("*.*")}
        actual_files: set[str] = {p.name for p in actual_dir.rglob("*.*")}
        for expected_step in expected_files:
            assert expected_step in actual_files
            if expected_step.endswith(".yaml"):
                expected, actual = test_mp.common.get_yaml_content(
                    expected=expected_dir / expected_step, actual=actual_dir / expected_step
                )
                assert actual == expected

    def wrapper(playbook_path: Path) -> None:
        mocked_repo: Path = tmp_path / playbook_path.parent.name
        shutil.copytree(playbook_path.parent, mocked_repo)

        playbook_repo: PlaybooksRepo = PlaybooksRepo(mocked_repo)

        playbook: Path = mocked_repo / playbook_path.name
        playbook_repo.deconstruct_playbook(playbook)

        out_playbook: Path = playbook_repo.out_dir / playbook.stem

        actual_files: set[str] = {p.name for p in out_playbook.rglob("*.*")}
        expected_files: set[str] = {p.name for p in non_built_playbook_path.rglob("*.*")}
        assert actual_files == expected_files

        expected, actual = test_mp.common.get_yaml_content(
            expected=non_built_playbook_path / mp.core.constants.TRIGGER_FILE_NAME,
            actual=out_playbook / mp.core.constants.TRIGGER_FILE_NAME,
        )
        assert actual == expected

        expected, actual = test_mp.common.get_yaml_content(
            expected=non_built_playbook_path / mp.core.constants.OVERVIEWS_FILE_NAME,
            actual=out_playbook / mp.core.constants.OVERVIEWS_FILE_NAME,
        )
        assert DeepDiff(expected, actual, ignore_order=True) == NO_DIFF

        expected, actual = test_mp.common.get_yaml_content(
            expected=non_built_playbook_path / mp.core.constants.DEFINITION_FILE,
            actual=out_playbook / mp.core.constants.DEFINITION_FILE,
        )
        assert actual == expected

        expected, actual = test_mp.common.get_yaml_content(
            expected=non_built_playbook_path / mp.core.constants.DISPLAY_INFO_FILE_MAME,
            actual=out_playbook / mp.core.constants.DISPLAY_INFO_FILE_MAME,
        )
        assert actual == expected

        non_built_playbook_path_steps_dir = non_built_playbook_path / mp.core.constants.STEPS_DIR
        out_playbook_steps_dir = out_playbook / mp.core.constants.STEPS_DIR

        compare_nested_files(non_built_playbook_path_steps_dir, out_playbook_steps_dir)

        non_built_playbook_path_widget_dir = non_built_playbook_path / mp.core.constants.WIDGETS_DIR
        out_playbook_widget_dir = out_playbook / mp.core.constants.WIDGETS_DIR

        compare_nested_files(non_built_playbook_path_widget_dir, out_playbook_widget_dir)

    return wrapper
