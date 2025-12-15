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
from mp.validate.pre_build_validation.playbooks.steps_parameters_validation import (
    StepParamsValidation,
)

from .common import update_single_step

if TYPE_CHECKING:
    from pathlib import Path


class TestStepParamsValidation:
    validator_runner: StepParamsValidation = StepParamsValidation()

    def test_all_params_valid(self, non_built_playbook_path: Path) -> None:
        self.validator_runner.run(non_built_playbook_path)

    def test_assigned_users_for_automatic_step_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {
                "is_automatic": True,
                "parameters": [{"name": "AssignedUsers", "value": "testuser@google.com"}],
            },
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "AssignedUsers is not allowed for automatic steps." in str(excinfo.value)

    def test_pending_action_timeout_too_low_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {"parameters": [{"name": "PendingActionTimeout", "value": "299"}]},
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "PendingActionTimeout must be at least 300 seconds." in str(excinfo.value)

    def test_async_action_timeout_too_high_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {"parameters": [{"name": "AsyncActionTimeout", "value": "1209601"}]},
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "AsyncActionTimeout must positive number less than 14 days (in seconds)." in str(
            excinfo.value
        )

    def test_async_action_timeout_not_positive_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {"parameters": [{"name": "AsyncActionTimeout", "value": "0"}]},
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "AsyncActionTimeout must positive number less than 14 days (in seconds)." in str(
            excinfo.value
        )

    def test_async_polling_interval_too_low_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {"parameters": [{"name": "AsyncPollingInterval", "value": "29"}]},
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "AsyncPollingInterval must be at least 30 seconds." in str(excinfo.value)

    def test_fail_async_polling_interval_ge_timeout(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {
                "parameters": [
                    {"name": "AsyncActionTimeout", "value": "299"},
                    {"name": "AsyncPollingInterval", "value": "300"},
                ]
            },
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        assert "AsyncPollingInterval must be less than AsyncActionTimeout." in str(excinfo.value)

    def test_all_errors_in_step_fail(self, temp_non_built_playbook: Path) -> None:
        update_single_step(
            temp_non_built_playbook,
            {
                "is_automatic": True,
                "parameters": [
                    {"name": "AssignedUsers", "value": "testuser@google.com"},
                    {"name": "PendingActionTimeout", "value": "299"},
                    {"name": "AsyncActionTimeout", "value": "1209601"},
                    {"name": "AsyncPollingInterval", "value": "1209602"},
                ],
            },
        )

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg = str(excinfo.value)
        assert "AssignedUsers is not allowed for automatic steps." in error_msg
        assert "PendingActionTimeout must be at least 300 seconds." in error_msg
        assert "AsyncActionTimeout must positive number less than 14 days " in error_msg
        assert "AsyncPollingInterval must be less than AsyncActionTimeout." in error_msg
