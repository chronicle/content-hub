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
from TIPCommon.smp_time import unix_now
from TIPCommon.types import SingleJson

from ...actions.SubmitEntities import (
    SubmitEntities,
    SUCCESS_MESSAGE,
    PENDING_MESSAGE,
    NONE_UPDATED_MESSAGE,
    TIMEOUT_MESSAGE,
)
import web_risk.core.WebRiskConstants as Constants

from ...tests.common import CONFIG
from ...tests.core.session import ApiSession
from integration_testing.common import get_def_file_content
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_MESSAGE = (
    f"Error executing action \"{Constants.SUBMIT_ENTITIES_SCRIPT_NAME}\"\n"
    f"Reason:"
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE} No service account, workload identity "
    "email were provided, or missing mandatory fields for service account"
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_MESSAGE} Impersonation is not allowed for the "
    "provided service account invalid-sa@domain.com. Please add the "
    "\"Service Account Token Creator\" role to the service account:"
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_RUNNING: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)
ACTION_CONFIG_RUNNING["additional_data"] = (
    "{\"https://testsafebrowsing.appspot.com/s/malware.html\": {\"name\": "
    "\"projects/508138417679/operations/11895063640312853845\"}}"
)


class TestAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS
    )
    def test_without_creds(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        SubmitEntities().run()

        assert len(script_session.request_history) == 0
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
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        SubmitEntities().run()

        assert len(script_session.request_history) >= 1
        assert (
            script_session.request_history[-1]
            .response.json().get("error", {}).get("message")
            == "Not found; Gaia id not found for email invalid-sa@domain.com"
        )
        assert script_session.request_history[-1].response.status_code == 404
        assert INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestEnrichment:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
    )
    def test_no_entities(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        SubmitEntities().run()

        assert len(script_session.request_history) >= 1
        assert action_output.results == ActionOutput(
            output_message=NONE_UPDATED_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG,
        entities=[
            DomainEntityInfo(
                identifier="https://domaiN.com",
                additional_properties={
                    "Environment": "Default Environment",
                    "OriginalIdentifier": "https://domain.com",
                },
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type=EntityTypesEnum.URL.value,
                is_pivot=False,
                is_artifact=False,
                is_enriched=False,
                is_internal=False,
                is_suspicious=False,
                is_vulnerable=False,
            ),
            DomainEntityInfo(
                identifier="https://testSafebrowsing.appspot.com/s/malware.html",
                additional_properties={
                    "Environment": "Default Environment",
                    "OriginalIdentifier": (
                        "https://testsafebrowsing.appspot.com/s/malware.html"
                    )
                },
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type=EntityTypesEnum.URL.value,
                is_pivot=False,
                is_artifact=False,
                is_enriched=False,
                is_internal=False,
                is_suspicious=False,
                is_vulnerable=False,
            )
        ]
    )
    def test_valid_invalid(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        set_is_first_run_to_true()
        action_ = SubmitEntities()
        action_.soar_action.execution_deadline_unix_time_ms = unix_now() + 60_000
        action_.soar_action.async_total_duration_deadline = unix_now() + 60_000
        action_.soar_action.session = script_session
        action_.run()

        assert len(script_session.request_history) >= 3
        assert (
            "https://domain.com" ==
            script_session.request_history[-2].request
            .kwargs["json"]["submission"]["uri"]
        )
        assert (
            "https://testsafebrowsing.appspot.com/s/malware.html" ==
            script_session.request_history[-1].request
            .kwargs["json"]["submission"]["uri"]
        )
        assert action_output.results.output_message == PENDING_MESSAGE
        assert isinstance(action_output.results.result_value, str)
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
        assert action_output.results.json_output.json_result[1]["Entity"] == (
            "https://testsafebrowsing.appspot.com/s/malware.html"
        )
        assert action_output.results.json_output.json_result[1]["EntityResult"]

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_RUNNING,
        entities=[
            DomainEntityInfo(
                identifier="https://testSafebrowsing.appspot.com/s/malware.html",
                additional_properties={
                    "Environment": "Default Environment",
                    "OriginalIdentifier": (
                        "https://testsafebrowsing.appspot.com/s/malware.html"
                    )
                },
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type=EntityTypesEnum.URL.value,
                is_pivot=False,
                is_artifact=False,
                is_enriched=False,
                is_internal=False,
                is_suspicious=False,
                is_vulnerable=False,
            )
        ]
    )
    def test_second_run(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        set_is_first_run_to_false()
        action_ = SubmitEntities()
        action_.soar_action.execution_deadline_unix_time_ms = unix_now() + 60_000
        action_.soar_action.async_total_duration_deadline = unix_now() + 60_000
        action_.soar_action.session = script_session
        action_.run()

        assert len(script_session.request_history) >= 2
        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(
                "https://testsafebrowsing.appspot.com/s/malware.html"
            )
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.json_output.json_result[0]["Entity"] == (
            "https://testsafebrowsing.appspot.com/s/malware.html"
        )
        assert action_output.results.json_output.json_result[0]["EntityResult"]

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_RUNNING,
        entities=[
            DomainEntityInfo(
                identifier="https://testSafebrowsing.appspot.com/s/malware.html",
                additional_properties={
                    "Environment": "Default Environment",
                    "OriginalIdentifier": (
                        "https://testsafebrowsing.appspot.com/s/malware.html"
                    )
                },
                alert_identifier="test-alert",
                case_identifier=1,
                creation_time=unix_now(),
                modification_time=unix_now(),
                entity_type=EntityTypesEnum.URL.value,
                is_pivot=False,
                is_artifact=False,
                is_enriched=False,
                is_internal=False,
                is_suspicious=False,
                is_vulnerable=False,
            )
        ]
    )
    def test_second_run_timeout(
            self,
            script_session: ApiSession,
            action_output: MockActionOutput,
    ) -> None:
        set_is_first_run_to_false()
        action_ = SubmitEntities()
        action_.soar_action.execution_deadline_unix_time_ms = unix_now() + 60_000
        action_.soar_action.session = script_session
        action_.run()

        assert len(script_session.request_history) >= 1
        assert TIMEOUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
