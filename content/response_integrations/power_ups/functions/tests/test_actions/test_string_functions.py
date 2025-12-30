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

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import StringFunctions


@set_metadata(
    integration_config={},
    parameters={
        "Param 1": "_",
        "Param 2": "_SPACE_",
        "Input": "Underscore_to_space",
        "Function": "Replace",
    },
)
def test_string_function_replace(
    action_output: MockActionOutput,
) -> None:
    StringFunctions.main()

    assert action_output.report.output_message == (
        "Underscore_to_space successfully converted to Underscore to space with replace function"
    )
    assert action_output.report.result_value == "Underscore to space"
    assert action_output.report.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config={},
    parameters={
        "Param 1": "_",
        "Param 2": "_SPACE_",
        "Input": "Underscore_to_space",
        "Function": "Regex Replace",
    },
)
def test_string_function_regex_replace(
    action_output: MockActionOutput,
) -> None:
    StringFunctions.main()

    assert action_output.report.output_message == (
        "Underscore_to_space successfully converted to "
        "Underscore to space with regex replace function"
    )
    assert action_output.report.result_value == "Underscore to space"
    assert action_output.report.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config={},
    parameters={
        "Param 1": r"([a-z])([A-Z])",
        "Param 2": r"\1_SPACE_\2",
        "Input": "CamelCaseToWords",
        "Function": "Regex Replace",
    },
)
def test_string_function_regex_replace_regex_param(
    action_output: MockActionOutput,
) -> None:
    StringFunctions.main()

    assert action_output.report.output_message == (
        "CamelCaseToWords successfully converted to Camel Case To Words with regex replace function"
    )
    assert action_output.report.result_value == "Camel Case To Words"
    assert action_output.report.execution_state == ExecutionState.COMPLETED
