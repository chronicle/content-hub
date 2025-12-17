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

from mp.core.data_models.playbooks.step.metadata import Step, StepType
from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.playbooks.loop_step_validation import LoopStepValidation

from .common import ingest_new_steps

if TYPE_CHECKING:
    from pathlib import Path

# region Constants
START_LOOP_1 = Step(
    name="Start Loop 1",
    description="",
    identifier="start_loop_1",
    original_step_id="start_loop_1",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="Start Loop 1",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    start_loop_step_id="start_loop_1",
    type_=StepType.FOR_EACH_START_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    parallel_actions=[],
)

END_LOOP_1 = Step(
    name="End Loop 1",
    description="",
    identifier="end_loop_1",
    original_step_id="end_loop_1",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="End Loop 1",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    start_loop_step_id="start_loop_1",
    type_=StepType.FOR_EACH_END_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    parallel_actions=[],
)

START_LOOP_2 = Step(
    name="Start Loop 2",
    description="",
    identifier="start_loop_2",
    original_step_id="start_loop_2",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="Start Loop 2",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    start_loop_step_id="start_loop_2",
    type_=StepType.FOR_EACH_START_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    parallel_actions=[],
)

END_LOOP_2 = Step(
    name="End Loop 2",
    description="",
    identifier="end_loop_2",
    original_step_id="end_loop_2",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="End Loop 2",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    type_=StepType.FOR_EACH_END_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    start_loop_step_id="start_loop_2",
    parallel_actions=[],
)

END_LOOP_1_INVALID_START_ID = Step(
    name="End Loop 1",
    description="",
    identifier="end_loop_1",
    original_step_id="end_loop_1",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="End Loop 1",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    type_=StepType.FOR_EACH_END_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    start_loop_step_id="non_existent_start_loop",
    parallel_actions=[],
)

END_LOOP_1_NULL_START_ID = Step(
    name="End Loop 1",
    description="",
    identifier="end_loop_1",
    original_step_id="end_loop_1",
    playbook_id="playbook1",
    parent_step_ids=[],
    parent_step_id="",
    instance_name="End Loop 1",
    is_automatic=True,
    is_skippable=False,
    action_provider="",
    action_name="",
    type_=StepType.FOR_EACH_END_LOOP,
    parameters=[],
    auto_skip_on_failure=False,
    is_debug_mock_data=False,
    is_touched_by_ai=False,
    start_loop_step_id=None,
    parallel_actions=[],
)


class TestLoopStepValidation:
    validator_runner: LoopStepValidation = LoopStepValidation()

    def test_playbook_without_loops_valid(self, temp_non_built_playbook: Path) -> None:
        self.validator_runner.run(temp_non_built_playbook)

    def test_playbook_with_loops_valid(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(temp_non_built_playbook, [START_LOOP_1, END_LOOP_1])
        self.validator_runner.run(temp_non_built_playbook)

    def test_playbook_with_multiple_valid_loops(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(
            temp_non_built_playbook, [START_LOOP_1, END_LOOP_1, START_LOOP_2, END_LOOP_2]
        )
        self.validator_runner.run(temp_non_built_playbook)

    def test_playbook_with_multiple_loops_one_invalid(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(
            temp_non_built_playbook,
            [START_LOOP_1, END_LOOP_1_INVALID_START_ID, START_LOOP_2, END_LOOP_2],
        )
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg = str(excinfo.value)
        assert "Step <Start Loop 1> is missing a matching end loop step" in error_msg

    def test_more_start_loops_than_end_loops(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(temp_non_built_playbook, [START_LOOP_1, START_LOOP_2, END_LOOP_1])
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg = str(excinfo.value)
        assert "There are missing 1 end loop steps." in error_msg
        assert "Step <Start Loop 2> is missing a matching end loop step" in error_msg

    def test_more_end_loops_than_start_loops(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(temp_non_built_playbook, [START_LOOP_1, END_LOOP_1, END_LOOP_2])
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg: str = str(excinfo.value)
        assert "There are missing 1 start loop steps." in error_msg

    def test_missing_start_loop_identifier(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(temp_non_built_playbook, [START_LOOP_1, END_LOOP_1_INVALID_START_ID])
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg: str = str(excinfo.value)
        assert "Step <Start Loop 1> is missing a matching end loop step" in error_msg

    def test_null_start_loop_identifier(self, temp_non_built_playbook: Path) -> None:
        ingest_new_steps(temp_non_built_playbook, [START_LOOP_1, END_LOOP_1_NULL_START_ID])
        with pytest.raises(FatalValidationError) as excinfo:
            self.validator_runner.run(temp_non_built_playbook)

        error_msg = str(excinfo.value)
        assert "Step <Start Loop 1> is missing a matching end loop step" in error_msg
