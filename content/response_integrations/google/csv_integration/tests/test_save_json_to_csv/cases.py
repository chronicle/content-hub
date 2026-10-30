# Copyright 2026 Google LLC
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

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput

from csv_integration.tests.common import get_mock_data


def create_success_output(file_path: str) -> ActionOutput:
    """Creates a standard ActionOutput object for a successful run."""
    json_output_content: dict[str, str] = {"filepath": file_path}
    json_output_model: ActionJsonOutput = ActionJsonOutput(
        json_result=json_output_content
    )

    success_message: str = (
        "Successfully transformed the JSON object and saved it to the "
        "provided file path."
    )

    return ActionOutput(
        output_message=success_message,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=json_output_model,
    )


FILE_PATH: str = "/tmp/output.csv"
HAPPY_PATH_PARAMS: dict[str, str] = {
    "File Path": FILE_PATH,
    "JSON Object": get_mock_data("valid_json_list"),
    "Overwrite": "False",
}
HAPPY_PATH_RESULTS: ActionOutput = create_success_output(FILE_PATH)

SINGLE_OBJECT_FILE_PATH: str = "/tmp/single.csv"
SINGLE_OBJECT_PARAMS: dict[str, str] = {
    "File Path": SINGLE_OBJECT_FILE_PATH,
    "JSON Object": get_mock_data("single_object_json"),
    "Overwrite": "False",
}
SINGLE_OBJECT_RESULTS: ActionOutput = create_success_output(
    SINGLE_OBJECT_FILE_PATH
)

VERTICAL_UNPACK_FILE_PATH: str = "/tmp/vertical_unpack.csv"
VERTICAL_UNPACK_PARAMS: dict[str, str] = {
    "File Path": VERTICAL_UNPACK_FILE_PATH,
    "JSON Object": get_mock_data("complex_nested_json"),
    "Overwrite": "True",
    "Advanced Nested JSON Handling": "True",
}
VERTICAL_UNPACK_RESULTS: ActionOutput = create_success_output(
    VERTICAL_UNPACK_FILE_PATH
)

INVALID_JSON_FILE_PATH: str = "/tmp/invalid.csv"
INVALID_JSON_PARAMS: dict[str, str] = {
    "File Path": INVALID_JSON_FILE_PATH,
    "JSON Object": get_mock_data("invalid_json_string"),
    "Overwrite": "False",
}
INVALID_JSON_MESSAGE: str = (
    "Error executing action Save JSON to CSV. Reason: The JSON "
    "structure is invalid"
)
INVALID_JSON_RESULTS: ActionOutput = ActionOutput(
    output_message=INVALID_JSON_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)
