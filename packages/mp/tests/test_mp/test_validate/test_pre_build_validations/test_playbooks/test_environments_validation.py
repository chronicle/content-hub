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
import shutil
from pathlib import Path

from hypothesis.extra.cli import pytest

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.playbooks.meta.metadata import NonBuiltPlaybookMetadata, PlaybookMetadata
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.playbooks.environments_validation import (
    VALID_ENVIRONMENTS,
    EnvironmentsValidation,
)


class TestEnvironmentsValidation:
    validator_runner: EnvironmentsValidation = EnvironmentsValidation()

    def test_all_environments_valid(self, tmp_path: Path, non_built_playbook_path: Path) -> None:
        playbook_path = self._set_playbook_environments(
            tmp_path, non_built_playbook_path, environments=list(VALID_ENVIRONMENTS)
        )
        self.validator_runner.run(playbook_path)

    def test_all_environments_invalid(self, tmp_path: Path, non_built_playbook_path: Path) -> None:
        playbook_path = self._set_playbook_environments(
            tmp_path, non_built_playbook_path, environments=["personal env 1", "personal env 2"]
        )

        with pytest.raises(NonFatalValidationError):
            self.validator_runner.run(playbook_path)

    def test_one_invalid_one_valid(self, tmp_path: Path, non_built_playbook_path: Path) -> None:
        playbook_path = self._set_playbook_environments(
            tmp_path,
            non_built_playbook_path,
            environments=["personal env 2", *list(VALID_ENVIRONMENTS)],
        )

        with pytest.raises(NonFatalValidationError):
            self.validator_runner.run(playbook_path)

    def _set_playbook_environments(
        self, tmp_path: Path, non_built_playbook_path: Path, environments: list[str]
    ) -> Path:
        playbook_path = tmp_path / non_built_playbook_path.name
        shutil.copytree(non_built_playbook_path, playbook_path)
        definition_path = playbook_path / mp.core.constants.DEFINITION_FILE

        def_file: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook_path)
        def_file.environments = environments
        non_built_def_file: NonBuiltPlaybookMetadata = def_file.to_non_built()
        mp.core.file_utils.save_yaml(non_built_def_file, definition_path)

        return playbook_path
