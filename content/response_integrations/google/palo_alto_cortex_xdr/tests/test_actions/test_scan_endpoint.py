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
import datetime

from TIPCommon.base.action import ExecutionState, EntityTypesEnum

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from palo_alto_cortex_xdr.actions import ScanEndpoint
from palo_alto_cortex_xdr.tests import common
from palo_alto_cortex_xdr.tests.core.product import PaloAltoCortexXDR
from palo_alto_cortex_xdr.tests.core.session import PaloAltoCortexXDRSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)

HOSTNAME_ENTITY = create_entity(
    identifier=common.ENDPOINT_DATA["host_name"], type_=EntityTypesEnum.HOST_NAME
)
IP_ENTITY = create_entity(
    identifier=common.MOCK_DATA["endpoint_data_ip"]["ip"][0],
    type_=EntityTypesEnum.ADDRESS,
)

DEFAULT_PARAMS = {
    "Incident ID": "12345",
}

HOSTNAME = common.ENDPOINT_DATA["host_name"]
IP_ADDRESS = common.MOCK_DATA["endpoint_data_ip"]["ip"][0]

NOT_FOUND_ENTITY_IDENTIFIER = "not.found.com"
NOT_FOUND_ENTITY = create_entity(
    identifier=NOT_FOUND_ENTITY_IDENTIFIER, type_=EntityTypesEnum.HOST_NAME
)
NOT_FOUND_OUTPUT_MESSAGE = (
    "The scan didn't complete for all of the provided endpoints in Palo Alto XDR.\n"
    "The following entities were "
    f"not found in Palo Alto XDR: {NOT_FOUND_ENTITY_IDENTIFIER}."
)


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[HOSTNAME_ENTITY, IP_ENTITY],
    input_context={
        "async_total_duration_deadline": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_scan_endpoint_success(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for successful execution of the ScanEndpoint action (async).
    """
    palo_alto_cortex_xdr.add_endpoint(copy.deepcopy(common.ENDPOINT_DATA))
    palo_alto_cortex_xdr.add_endpoint(
        copy.deepcopy(common.MOCK_DATA["endpoint_data_ip"])
        )

    ScanEndpoint.main()

    assert len(script_session.request_history) == 5
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    integration_config=common.CONFIG,
    parameters=DEFAULT_PARAMS,
    entities=[NOT_FOUND_ENTITY],
)
def test_scan_endpoint_not_found(
    script_session: PaloAltoCortexXDRSession,
    action_output: MockActionOutput,
) -> None:
    """
    Test for ScanEndpoint action when an endpoint is not found.
    """
    ScanEndpoint.main()

    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == NOT_FOUND_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED
