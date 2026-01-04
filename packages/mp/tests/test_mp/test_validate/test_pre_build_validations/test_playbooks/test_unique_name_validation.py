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
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.playbooks.unique_name_validation import (
    UniqueNameValidation,
)

from .common import update_display_info


def _setup(temp_non_built_playbook: Path) -> None:
    duplicate_path: Path = temp_non_built_playbook.parent / f"{temp_non_built_playbook.name}2"
    if duplicate_path.exists():
        shutil.rmtree(duplicate_path)
    shutil.copytree(temp_non_built_playbook, duplicate_path)


class TestUniqueNameValidation:
    validator_runner: UniqueNameValidation = UniqueNameValidation()

    @patch("mp.core.file_utils.get_playbook_base_folders_paths")
    @patch("mp.core.file_utils.get_or_create_playbook_repo_base_path")
    def test_unique_name_validation_success(
        self,
        mock_get_playbook_repository_base_path: MagicMock,
        mock_get_playbook_base_folders_paths: MagicMock,
        temp_non_built_playbook: Path,
    ) -> None:
        _setup(temp_non_built_playbook)
        update_display_info(temp_non_built_playbook, {"content_hub_display_name": "test"})
        update_display_info(
            Path(f"{temp_non_built_playbook}2"), {"content_hub_display_name": "test2"}
        )
        mock_get_playbook_repository_base_path.return_value = temp_non_built_playbook.parent
        mock_get_playbook_base_folders_paths.return_value = [temp_non_built_playbook.parent]

        self.validator_runner.run(temp_non_built_playbook)

    @patch("mp.core.file_utils.get_playbook_base_folders_paths")
    @patch("mp.core.file_utils.get_or_create_playbook_repo_base_path")
    def test_duplicate_name_validation_fail(
        self,
        mock_get_playbook_repository_base_path: MagicMock,
        mock_get_playbook_base_folders_paths: MagicMock,
        temp_non_built_playbook: Path,
    ) -> None:
        _setup(temp_non_built_playbook)
        mock_get_playbook_repository_base_path.return_value = temp_non_built_playbook.parent
        mock_get_playbook_base_folders_paths.return_value = [temp_non_built_playbook.parent]
        update_display_info(temp_non_built_playbook, {"content_hub_display_name": "test"})
        update_display_info(
            Path(f"{temp_non_built_playbook}2"), {"content_hub_display_name": "test"}
        )
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "The playbook display name 'test' is already in use at the following" in str(excinfo)
