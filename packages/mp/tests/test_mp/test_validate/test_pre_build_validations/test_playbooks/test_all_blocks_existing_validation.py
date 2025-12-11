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

from mp.validate.pre_build_validation.playbooks.all_blocks_existing_validation import (
    AllBlocksExistValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestAllBlocksExistValidation:
    validator_runner: AllBlocksExistValidation = AllBlocksExistValidation()

    def test_all_blocks_exist_success(self, temp_playbook: Path):
        self.validator_runner.run(temp_playbook)
