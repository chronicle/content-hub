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

from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.playbooks.roles_validation import RolesValidation

from .common import update_single_overview_roles

if TYPE_CHECKING:
    from pathlib import Path


class TestRolesValidation:
    validator_runner: RolesValidation = RolesValidation()

    def test_all_roles_valid(self, non_built_playbook_path: Path) -> None:
        self.validator_runner.run(non_built_playbook_path)

    def test_invalid_roles_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_overview_roles(temp_non_built_playbook, ["invalid_role"])

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "Found invalid roles in playbook overviews: invalid_role." in str(excinfo.value)

    def test_mixed_roles_fail(self, temp_non_built_playbook) -> None:
        update_single_overview_roles(temp_non_built_playbook, ["invalid_role", "Tier1"])

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "Found invalid roles in playbook overviews: invalid_role." in str(excinfo.value)
