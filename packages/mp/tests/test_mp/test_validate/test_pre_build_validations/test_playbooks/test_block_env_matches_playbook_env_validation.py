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

import pytest

from mp.core.constants import VALID_ENVIRONMENTS
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.playbooks.block_env_matches_playbook_env_validation import (
    BlockEnvMatchesPlaybookEnvValidation,
)

from .common import update_playbook_definition

if TYPE_CHECKING:
    from pathlib import Path

ENV1: str = "env1"
ENV2: str = "env2"
ENV3: str = "env3"


class TestBlockEnvMatchesPlaybookEnvValidation:
    validator_runner: BlockEnvMatchesPlaybookEnvValidation = BlockEnvMatchesPlaybookEnvValidation()

    def test_blocks_has_all_env_valid(self, temp_playbooks_repo: Path) -> None:
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_playbook",
            {"environments": [ENV1, ENV2, ENV3]},
        )
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_block", {"environments": ["env1", "env2", "env3"]}
        )
        self.validator_runner.run(temp_playbooks_repo / "mock_non_built_playbook")

    def test_block_missing_all_env_fail(self, temp_playbooks_repo: Path) -> None:
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_playbook",
            {"environments": VALID_ENVIRONMENTS},
        )
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_block", {"environments": []}
        )
        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_playbooks_repo / "mock_non_built_playbook")

        error_msg: str = str(excinfo.value)
        assert "*" in error_msg
        assert "Default Environment" in error_msg

    def test_block_has_all_env_valid(self, temp_playbooks_repo: Path) -> None:
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_playbook",
            {"environments": [ENV1, ENV2, ENV3]},
        )
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_block", {"environments": ["*"]}
        )
        self.validator_runner.run(temp_playbooks_repo / "mock_non_built_playbook")

    def test_block_missing_env_fail(self, temp_playbooks_repo: Path) -> None:
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_playbook",
            {"environments": [ENV1, ENV2, ENV3]},
        )
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_block", {"environments": [ENV1]}
        )
        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_playbooks_repo / "mock_non_built_playbook")

        error_msg: str = str(excinfo.value)
        assert ENV2 in error_msg
        assert ENV3 in error_msg

    def test_playbook_all_env_block_missing_some_fail(self, temp_playbooks_repo: Path) -> None:
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_playbook",
            {"environments": ["*"]},
        )
        update_playbook_definition(
            temp_playbooks_repo / "mock_non_built_block", {"environments": [ENV1]}
        )
        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_playbooks_repo / "mock_non_built_playbook")
        assert "has missing environments from its playbook env {'*'}" in str(excinfo.value)
