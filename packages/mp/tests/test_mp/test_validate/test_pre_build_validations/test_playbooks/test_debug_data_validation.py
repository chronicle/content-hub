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
from mp.validate.pre_build_validation.playbooks.debug_data_validation import (
    DebugDataValidation,
)

from .common import update_display_info, update_playbook_definition, update_step_with_debug_data

if TYPE_CHECKING:
    from pathlib import Path


class TestDebugDataValidation:
    validator_runner: DebugDataValidation = DebugDataValidation()

    def test_valid_debug_data(self, temp_non_built_playbook: Path) -> None:
        update_display_info(temp_non_built_playbook, {"allowed_debug_data": True})
        update_playbook_definition(temp_non_built_playbook, {"is_debug_mode": False})
        update_step_with_debug_data(
            temp_non_built_playbook, is_debug_mock_data=False, has_debug_data=True
        )
        self.validator_runner.run(temp_non_built_playbook)

    def test_is_debug_mock_data_true_fail(self, temp_non_built_playbook: Path) -> None:
        update_display_info(temp_non_built_playbook, {"allowed_debug_data": True})
        update_playbook_definition(temp_non_built_playbook, {"is_debug_mode": False})
        update_step_with_debug_data(
            temp_non_built_playbook, is_debug_mock_data=True, has_debug_data=True
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "debug mode cannot be enabled. Please disable it." in str(excinfo.value)

    def test_allowed_debug_data_false_fail(self, temp_non_built_playbook: Path) -> None:
        update_display_info(temp_non_built_playbook, {"allowed_debug_data": False})
        update_playbook_definition(temp_non_built_playbook, {"is_debug_mode": False})
        update_step_with_debug_data(
            temp_non_built_playbook, is_debug_mock_data=False, has_debug_data=True
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert (
            "playbook contains debug data, but 'acknowledge_debug_data_included' is set to False"
            " in the display info file. Set 'acknowledge_debug_data_included' to True"
        ) in str(excinfo.value)

    def test_is_debug_mode_true_fail(self, temp_non_built_playbook: Path) -> None:
        update_display_info(temp_non_built_playbook, {"allowed_debug_data": True})
        update_playbook_definition(temp_non_built_playbook, {"is_debug_mode": True})
        update_step_with_debug_data(
            temp_non_built_playbook, is_debug_mock_data=False, has_debug_data=True
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert (
            "Playbook Simulator (definition.yaml/'is_debug_mode') cannot be "
            "enabled. Please disable it."
        ) in str(excinfo.value)

    def test_all_errors_fail(self, temp_non_built_playbook: Path) -> None:
        update_display_info(temp_non_built_playbook, {"allowed_debug_data": False})
        update_step_with_debug_data(
            temp_non_built_playbook, is_debug_mock_data=True, has_debug_data=True
        )
        update_playbook_definition(temp_non_built_playbook, {"is_debug_mode": True})

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg = str(excinfo.value)
        assert "debug mode cannot be enabled. Please disable it." in error_msg
        assert (
            "The playbook contains debug data, but 'acknowledge_debug_data_included' "
            "is set to False in the display info file. "
            "Set 'acknowledge_debug_data_included' to True to allow this data."
        ) in error_msg
        assert (
            "Playbook Simulator (definition.yaml/'is_debug_mode') cannot be "
            "enabled. Please disable it."
        ) in error_msg
