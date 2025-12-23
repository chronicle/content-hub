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

from mp.core.constants import OVERVIEWS_FILE_NAME
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.playbooks.block_overview_validation import (
    BlockDoesNotContainAnOverviewValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestBlockOverviewValidation:
    validator_runner: BlockDoesNotContainAnOverviewValidation = (
        BlockDoesNotContainAnOverviewValidation()
    )

    def test_valid_block_success(self, temp_non_built_block: Path) -> None:
        self.validator_runner.run(temp_non_built_block)

    def test_invalid_block_fail(
        self, temp_non_built_block: Path, temp_non_built_playbook: Path
    ) -> None:
        shutil.copy(temp_non_built_playbook / OVERVIEWS_FILE_NAME, temp_non_built_block)
        with pytest.raises(NonFatalValidationError, match="Block cannot have overviews"):
            self.validator_runner.run(temp_non_built_block)

    def test_run_on_playbook_success(self, temp_non_built_playbook: Path) -> None:
        self.validator_runner.run(temp_non_built_playbook)
