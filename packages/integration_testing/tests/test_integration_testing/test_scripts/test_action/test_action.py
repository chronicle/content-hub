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

from TIPCommon.base.action import ExecutionState

from integration_testing.common import set_is_first_run_to_true
from integration_testing.set_meta import set_metadata

from .mock_action import MockAction

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


@set_metadata
def test_action_output(action_output: MockActionOutput) -> None:
    action: MockAction = MockAction()

    action.run()

    assert action_output.report is not None
    assert action_output.report.output_message
    assert action_output.report.result_value
    assert action_output.report.execution_state is ExecutionState.COMPLETED


@set_metadata
def test_is_test_run_defaults_to_false() -> None:
    action: MockAction = MockAction()

    assert not action.is_first_run


@set_metadata
def test_is_test_run_is_set_to_true() -> None:
    set_is_first_run_to_true()

    action: MockAction = MockAction()

    assert action.is_first_run
