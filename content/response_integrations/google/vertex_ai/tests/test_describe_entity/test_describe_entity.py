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

from soar_sdk.SiemplifyDataModel import DomainEntityInfo
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.action.data_models import EntityTypesEnum
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from ...actions.DescribeEntity import (
    DescribeEntity,
    SUCCESS_MESSAGE,
)
import vertex_ai.core.VertexAIConstants as Constants

from ...tests.common import CONFIG
from ...tests.core.session import ApiSession
from integration_testing.common import get_def_file_content
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_MESSAGE = (
    f"Error executing action \"{Constants.DESCRIBE_ENTITY_SCRIPT_NAME}\"\nReason: "
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


class TestAuth:

    @set_metadata(integration_config=CONFIG_WITHOUT_CREDS)
    def test_without_creds(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        DescribeEntity(script_name=Constants.DESCRIBE_ENTITY_SCRIPT_NAME).run()

        assert len(vertexai_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(integration_config=CONFIG_WITH_INVALID_EMAIL)
    def test_invalid_email(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        DescribeEntity(script_name=Constants.DESCRIBE_ENTITY_SCRIPT_NAME).run()

        assert len(vertexai_script_session.request_history) >= 0
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
        entities=[
            DomainEntityInfo(
                identifier="user@email.com",
                additional_properties={"Environment": "Default Environment"},
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type="UserUniqname",
                is_pivot=False,
                is_artifact=False,
                is_enriched=True,
                is_internal=True,
                is_suspicious=True,
                is_vulnerable=False,
            )
        ],
        external_context=MockExternalContext(),
    )
    def test_valid_run(
            self,
            vertexai_script_session: ApiSession,
            action_output: MockActionOutput,
            external_context: MockExternalContext,
    ) -> None:
        action = DescribeEntity(script_name=Constants.DESCRIBE_ENTITY_SCRIPT_NAME)
        action.soar_action.execution_deadline_unix_time_ms = unix_now() + 60_000
        action.soar_action.session = vertexai_script_session
        action.run()

        assert len(vertexai_script_session.request_history) >= 1

        assert SUCCESS_MESSAGE == action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output is not None

        cache_entry = external_context.get_row_value(
            context_type=DatabaseContextType.GLOBAL,
            property_key="cache_user@email.com_Default Environment",
            identifier="",
        )
        assert cache_entry is not None
