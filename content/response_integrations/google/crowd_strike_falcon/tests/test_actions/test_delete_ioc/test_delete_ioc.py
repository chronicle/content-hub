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

from typing import Any

import pytest
from crowd_strike_falcon.actions import DeleteIOC
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

WRONG_ENTITY_ID: str = "npatni-sysops"
WRONG_ENTITY: Entity = create_entity(WRONG_ENTITY_ID, EntityTypesEnum.IP_SET)
INTEGRATION_CUSTOMER_ID: str = "integration_cid_303"

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully deleted the following custom IOCs in Crowdstrike Falcon"
    f": {HOSTNAME_ENTITY_ID}"
    "\n"
)
FAILURE_OUTPUT_MESSAGE: str = (
    "All of the provided IOCs were not a part of Crowdstrike Falcon instance."
)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_delete_ioc_success(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        DeleteIOC.main()

        assert len(script_session.request_history) == 3
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        entities=[WRONG_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_delete_ioc_wrong_entity(
            self,
            script_session: CrowdStrikeFalconSession,
            action_output: MockActionOutput,
    ) -> None:
        DeleteIOC.main()

        assert len(script_session.request_history) == 1
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


    @set_metadata(
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_does_not_send_member_cid(
        self,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies authentication request does not contain member_cid
        when no CID is provided.
        """
        DeleteIOC.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_sends_integration_member_cid(
        self,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies auth request uses the integration's CID when provided."""
        DeleteIOC.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
