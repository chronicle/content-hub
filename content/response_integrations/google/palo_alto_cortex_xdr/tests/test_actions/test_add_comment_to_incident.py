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

from palo_alto_cortex_xdr.actions import AddCommentToIncident
from palo_alto_cortex_xdr.core.constants import INTEGRATION_NAME
from palo_alto_cortex_xdr.core.datamodels import Incident
from palo_alto_cortex_xdr.tests import common
from palo_alto_cortex_xdr.tests.core.product import PaloAltoCortexXDR
from palo_alto_cortex_xdr.tests.core.session import PaloAltoCortexXDRSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

INCIDENT: Incident = common.INCIDENT
COMMENT: str = "This is a test comment."
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully add a comment to an incident with ID {INCIDENT.incident_id} in "
    f"{INTEGRATION_NAME}."
)
DEFAULT_PARAMETERS: dict[str, str] = {
    "Incident ID": INCIDENT.incident_id,
    "Comment": COMMENT,
}

FAILED_PARAMETERS: dict[str, str] = {
    "Incident ID": str(common.INVALID_INCIDENT_ID),
    "Comment": COMMENT,
}



@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_add_comment_to_incident_action_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for successful execution of the AddCommentToIncident action.
    """
    palo_alto_cortex_xdr.cleanup_incidents()
    incident = copy.deepcopy(INCIDENT)
    palo_alto_cortex_xdr.add_incident(incident)

    AddCommentToIncident.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is None


@set_metadata(integration_config=common.CONFIG, parameters=FAILED_PARAMETERS)
def test_add_comment_to_incident_action_not_found_failure(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for failure execution of the AddCommentToIncident action when incident is
    not found.
    """
    palo_alto_cortex_xdr.cleanup_incidents()

    AddCommentToIncident.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.json_output is None
