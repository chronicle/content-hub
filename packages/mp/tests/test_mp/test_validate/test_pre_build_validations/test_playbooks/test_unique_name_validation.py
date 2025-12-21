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

from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo
from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.playbooks.unique_name_validation import (
    UniqueNameValidation,
)


def _setup(temp_non_built_playbook: Path) -> None:
    duplicate_path: Path = temp_non_built_playbook.parent / f"{temp_non_built_playbook.name}2"
    shutil.copytree(temp_non_built_playbook, duplicate_path)


class TestUniqueNameValidation:
    validator_runner: UniqueNameValidation = UniqueNameValidation()

    @patch("mp.core.file_utils.get_playbook_repository_base_path")
    def test_unique_name_validation_success(
        self,
        mock_get_playbook_repository_base_path: MagicMock,
        temp_non_built_playbook: Path,
    ) -> None:
        _setup(temp_non_built_playbook)
        mock_get_playbook_repository_base_path.return_value = temp_non_built_playbook.parent

        self.validator_runner.run(temp_non_built_playbook)
