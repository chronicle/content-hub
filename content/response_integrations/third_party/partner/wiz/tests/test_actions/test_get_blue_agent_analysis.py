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

import datetime
import json
from typing import TYPE_CHECKING

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from tests.core.product import Wiz
from tests.core.session import WizSession
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from wiz.actions import get_blue_agent_analysis
from wiz.core import constants

from .. import common

if TYPE_CHECKING:
    from collections.abc import Mapping

    from TIPCommon.types import SingleJson


THREAT_ID: str = "786ec97b-51e9-428a-b237-03452ef17de4"
SCRIPT_DEADLINE_TIME: datetime.datetime = (
    datetime.datetime.now() + datetime.timedelta(minutes=10)
)

ANALYSIS_COMPLETED: SingleJson = {
    "data": {
        "issue": {
            "threatDetectionDetails": {
                "aiAnalysis": {
                    "id": THREAT_ID,
                    "status": "COMPLETED",
                    "verdict": "MALICIOUS",
                    "analyzedAt": "2026-06-09T16:12:58.253716Z",
                    "severity": "CRITICAL",
                    "confidenceLevel": "HIGH",
                    "conclusion": "Container weather-ctf ...",
                    "investigationProcess": None
                }
            }
        }
    }
}

ANALYSIS_IN_PROGRESS: SingleJson = {
    "data": {
        "issue": {
            "threatDetectionDetails": {
                "aiAnalysis": {
                    "id": THREAT_ID,
                    "status": "IN_PROGRESS",
                    "verdict": None,
                    "analyzedAt": None,
                    "severity": None,
                    "confidenceLevel": None,
                    "conclusion": None,
                    "investigationProcess": None
                }
            }
        }
    }
}

ANALYSIS_NOT_SUPPORTED: SingleJson = {
    "data": {
        "issue": {
            "threatDetectionDetails": None
        }
    }
}

NOT_SUPPORTED_OUTPUT_MESSAGE: str = (
    "Blue Agent analysis is not available for threat"
    f" {THREAT_ID}."
)

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully returned Blue Agent analysis for threat {THREAT_ID} in Wiz."
)
PENDING_OUTPUT_MESSAGE: str = (
    f"Waiting for Wiz Blue Agent analysis for threat {THREAT_ID}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{constants.GET_BLUE_AGENT_ANALYSIS_SCRIPT_NAME}"\nReason:'
    f" Threat with ID {common.INVALID_ISSUE_ID} wasn't found in Wiz."
)

DEFAULT_PARAMETERS: Mapping[str, str] = {"Threat ID": THREAT_ID}
FAILED_PARAMETERS: Mapping[str, str] = {
    "Threat ID": common.INVALID_ISSUE_ID
}


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_blue_agent_analysis_completed(
    wiz: Wiz,
    script_session: WizSession,
    action_output: MockActionOutput,
) -> None:
    wiz.cleanup_threat_ai_analyses()
    wiz.add_threat_ai_analysis(THREAT_ID, ANALYSIS_COMPLETED)
    get_blue_agent_analysis.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_OUTPUT_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=ActionJsonOutput(json_result=ANALYSIS_COMPLETED),
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_blue_agent_analysis_in_progress(
    wiz: Wiz,
    script_session: WizSession,
    action_output: MockActionOutput,
) -> None:
    wiz.cleanup_threat_ai_analyses()
    wiz.add_threat_ai_analysis(THREAT_ID, ANALYSIS_IN_PROGRESS)
    get_blue_agent_analysis.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=PENDING_OUTPUT_MESSAGE,
        result_value=json.dumps({}),
        execution_state=ExecutionState.IN_PROGRESS,
        json_output=None,
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters=FAILED_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_blue_agent_analysis_not_found(
    wiz: Wiz,
    script_session: WizSession,
    action_output: MockActionOutput,
) -> None:
    wiz.cleanup_threat_ai_analyses()
    get_blue_agent_analysis.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMETERS,
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_get_blue_agent_analysis_not_supported(
    wiz: Wiz,
    script_session: WizSession,
    action_output: MockActionOutput,
) -> None:
    wiz.cleanup_threat_ai_analyses()
    wiz.add_threat_ai_analysis(THREAT_ID, ANALYSIS_NOT_SUPPORTED)
    get_blue_agent_analysis.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=NOT_SUPPORTED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
