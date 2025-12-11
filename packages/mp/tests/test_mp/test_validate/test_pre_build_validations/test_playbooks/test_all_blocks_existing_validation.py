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

import pytest

from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.playbooks.all_blocks_existing_validation import (
    AllBlocksExistValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestAllBlocksExistValidation:
    validator_runner: AllBlocksExistValidation = AllBlocksExistValidation()

    def test_all_blocks_exist_success(
        self, temp_non_built_playbook: Path, temp_non_built_block: Path
    ) -> None:
        destination_dir = temp_non_built_playbook.parent / temp_non_built_block.name
        shutil.copytree(temp_non_built_block, destination_dir)

        self.validator_runner.run(temp_non_built_playbook)

    def test_missing_block_fail(self, temp_non_built_playbook: Path) -> None:
        with pytest.raises(FatalValidationError, match="There are missing blocks"):
            self.validator_runner.run(temp_non_built_playbook)
