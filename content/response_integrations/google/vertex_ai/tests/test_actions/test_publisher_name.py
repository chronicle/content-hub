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

import pathlib
from TIPCommon.base.action import ExecutionState

import vertex_ai.core.VertexAIConstants as Constants
from vertex_ai.actions.ExecutePrompt import (
    ExecutePrompt,
    SUCCESS_MESSAGE,
)
from vertex_ai.tests.common import CONFIG
from vertex_ai.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

TEST_PUBLISHER_NAME = "test_some_publisher_name"
TEST_LOCATION = "test-europe-west4"
NEW_CONFIG = CONFIG.copy()
NEW_CONFIG["Publisher Name"] = TEST_PUBLISHER_NAME
NEW_CONFIG["API Root"] = f"https://{TEST_LOCATION}-aiplatform.googleapis.com"


@set_metadata(
    integration_config=NEW_CONFIG,
    parameters={
        "Model ID": "gemini-1.5-flash-002",
        "Text Prompt": "Sample text.",
        "Temperature": None,
        "Candidate Count": None,
        "Response MIME type": "text/plain",
        "Response Schema": None,
        "Max Input Tokens": None,
        "Max Output Tokens": None,
    },
)
def test_configure_initial_publisher_name(
    vertexai_script_session: ApiSession,
    action_output: MockActionOutput,
) -> None:
    action = ExecutePrompt(script_name=Constants.EXECUTE_PROMPT_SCRIPT_NAME)
    action.run()

    assert len(vertexai_script_session.request_history) >= 2
    publisher_name = TEST_PUBLISHER_NAME
    model_id = "gemini-1.5-flash-002"

    for item in vertexai_script_session.request_history:
        url_path = item.request.url.path
        if url_path.find("generateContent") != -1:
            assert url_path == (
                f"/v1/projects/domain/locations/{TEST_LOCATION}"
                f"/publishers/{publisher_name}"
                f"/models/{model_id}:generateContent"
            )

    assert SUCCESS_MESSAGE == action_output.results.output_message

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


NEW_PUBLISHER_NAME = "new_name"
NEW_CONFIG2 = CONFIG.copy()
NEW_CONFIG2["API Root"] = f"https://{TEST_LOCATION}-aiplatform.googleapis.com"


@set_metadata(
    integration_config=NEW_CONFIG2,
    parameters={
        "Model ID": "gemini-1.5-flash-002",
        "Text Prompt": "Sample text.",
        "Temperature": None,
        "Candidate Count": None,
        "Response MIME type": "text/plain",
        "Response Schema": None,
        "Max Input Tokens": None,
        "Max Output Tokens": None,
        "Publisher Name": NEW_PUBLISHER_NAME,
    },
)
def test_with_provided_publisher_name_in_action(
    vertexai_script_session: ApiSession,
    action_output: MockActionOutput,
) -> None:
    action = ExecutePrompt(script_name=Constants.EXECUTE_PROMPT_SCRIPT_NAME)
    action.run()

    assert len(vertexai_script_session.request_history) >= 2
    model_id = "gemini-1.5-flash-002"

    for item in vertexai_script_session.request_history:
        url_path = item.request.url.path
        if url_path.find("generateContent") != -1:
            assert url_path == (
                f"/v1/projects/domain/locations/{TEST_LOCATION}"
                f"/publishers/{NEW_PUBLISHER_NAME}"
                f"/models/{model_id}:generateContent"
            )

    assert SUCCESS_MESSAGE == action_output.results.output_message

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None
