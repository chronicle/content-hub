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

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.types import SingleJson

from vertex_ai.actions.AnalyzeEML import (
    AnalyzeEML,
    SUCCESS_MESSAGE,
    NOT_FOUND_FILES,
    NO_FILES_FOUND,
)
import vertex_ai.core.VertexAIConstants as Constants

from vertex_ai.tests.common import CONFIG
from vertex_ai.tests.core.session import ApiSession
from vertex_ai.tests.utils import (
    create_test_attachment,
    delete_test_attachments,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_MESSAGE = (
    f"Error executing action \"{Constants.ANALYZE_EML_SCRIPT_NAME}\"\nReason: "
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}No service account, workload identity "
    "email were provided, or missing mandatory fields for service account"
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE}Impersonation is not allowed for the "
    "provided service account invalid-sa@domain.com. Please add the "
    "\"Service Account Token Creator\" role to the service account:"
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ATTACHMENT_PATH = "test_attachments"
ATTACHMENT_NAME = "test_attachment.eml"

ACTION_CONFIG_WITH_FILES = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_FILES["Files To Analyze"] += "," + create_test_attachment(
    ATTACHMENT_PATH, ATTACHMENT_NAME
)


class TestAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS
    )
    def test_without_creds(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        AnalyzeEML(script_name=Constants.ANALYZE_EML_SCRIPT_NAME).run()

        assert len(vertexai_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG_WITH_INVALID_EMAIL
    )
    def test_invalid_email(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        AnalyzeEML(script_name=Constants.ANALYZE_EML_SCRIPT_NAME).run()

        assert len(vertexai_script_session.request_history) >= 1
        assert (
            vertexai_script_session.request_history[-1]
            .response.json().get("error", {}).get("message")
            == "Not found; Gaia id not found for email invalid-sa@domain.com"
        )
        assert vertexai_script_session.request_history[-1].response.status_code == 404
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestValid:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
    )
    def test_invalid_files(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        AnalyzeEML(script_name=Constants.ANALYZE_EML_SCRIPT_NAME).run()

        assert len(vertexai_script_session.request_history) >= 1
        assert action_output.results.output_message == ERROR_MESSAGE + NO_FILES_FOUND
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_FILES,
    )
    def test_valid_invalid_files(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        action = AnalyzeEML(script_name=Constants.ANALYZE_EML_SCRIPT_NAME)
        action.run()
        delete_test_attachments(ACTION_CONFIG_WITH_FILES["Files To Analyze"])

        assert len(vertexai_script_session.request_history) >= 2
        assert (
            SUCCESS_MESSAGE.format(
                ACTION_CONFIG_WITH_FILES["Files To Analyze"].split(",")[-1]
            )
            + NOT_FOUND_FILES.format(
                ACTION_CONFIG_WITH_FILES["Files To Analyze"].split(",")[0]
            )
            == action_output.results.output_message
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None
