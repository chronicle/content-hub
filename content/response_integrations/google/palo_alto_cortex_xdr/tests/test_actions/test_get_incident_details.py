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

import copy
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from ...actions import GetIncidentDetails
from ...core.constants import (
    GET_INCIDENT_DETAILS_ACTION_SCRIPT_NAME,
    PRODUCT,
    VENDOR,
)
from ...core.datamodels import Incident
from ...tests import common
from ...tests.core.product import PaloAltoCortexXDR
from ...tests.core.session import PaloAltoCortexXDRSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


INCIDENT: Incident = common.INCIDENT
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully returned information about incident with ID {INCIDENT.incident_id}"
    f" in {VENDOR} {PRODUCT}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{GET_INCIDENT_DETAILS_ACTION_SCRIPT_NAME}".\nReason: '
    "An error occurred: An error occurred while processing XDR public API - "
    "incident management - get_incident_extra_data - Incident not found"
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Incident ID": INCIDENT.incident_id,
    "Lowest Alert Severity": "Low",
    "Max Alerts To Return": "50",
}
FAILED_PARAMETERS: dict[str, str] = copy.deepcopy(DEFAULT_PARAMETERS)
FAILED_PARAMETERS["Incident ID"] = common.INVALID_INCIDENT_ID


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_get_incident_details_action_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    palo_alto_cortex_xdr.cleanup_incidents()
    incident = copy.deepcopy(INCIDENT)
    palo_alto_cortex_xdr.add_incident(incident)
    GetIncidentDetails.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert (
        action_output.results.json_output.json_result["incident_id"]
        == INCIDENT.incident_id
    )


@set_metadata(integration_config=common.CONFIG, parameters=FAILED_PARAMETERS)
def test_get_incident_details_action_failure(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    palo_alto_cortex_xdr.cleanup_incidents()
    incident = copy.deepcopy(INCIDENT)
    incident.incident_id = common.INVALID_INCIDENT_ID
    incident.raw_data["incident_id"] = common.INVALID_INCIDENT_ID
    palo_alto_cortex_xdr.add_incident(incident)
    GetIncidentDetails.main()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
