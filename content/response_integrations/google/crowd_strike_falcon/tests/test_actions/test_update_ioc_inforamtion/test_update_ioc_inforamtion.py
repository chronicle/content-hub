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
from crowd_strike_falcon.actions import UpdateIOCInformation
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import (
    CONFIG,
    CONFIG_PATH,
    HOSTNAME_ENTITY,
    HOSTNAME_ENTITY_ID,
    MOCK_DATA,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

WRONG_ENTITY_ID: str = "npatni-sysops"
WRONG_ENTITY: Entity = create_entity(WRONG_ENTITY_ID, EntityTypesEnum.IP_SET)
PARAMS: SingleJson = {
    "Description": "",
    "Source": "",
    "Expiration days": "",
    "Detect policy": True,
}
SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully updated the following entities in Crowdstrike Falcon: "
    f"{HOSTNAME_ENTITY_ID}\n"
)
FAILURE_OUTPUT_MESSAGE: str = (
    "No entities were updated in Crowdstrike Falcon."
)

INTEGRATION_CUSTOMER_ID: str = "integration_cid_for_update_ioc"
INTEGRATION_CONFIG_WITH_CID: SingleJson = CONFIG.copy()
INTEGRATION_CONFIG_WITH_CID["Customer ID"] = INTEGRATION_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_ioc_information_success(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        action_output: MockActionOutput,
    ) -> None:
        crowd_strike_falcon.add_entries(
            "custom_indicators",
            MOCK_DATA["iocs_entities_indicators_ids"]["resources"],
        )

        UpdateIOCInformation.main()

        assert len(script_session.request_history) == 4
        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        parameters=PARAMS,
        entities=[WRONG_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_update_ioc_information_wrong_entity(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        UpdateIOCInformation.main()

        assert len(script_session.request_history) == 1
        assert action_output.results.output_message == FAILURE_OUTPUT_MESSAGE
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.COMPLETED



@pytest.mark.usefixtures("script_session")
class TestTenantAuthentication:
    """Tests the tenant authentication logic based on integration configuration."""

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_when_no_cid_in_config(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is not sent when the integration config
        does not contain a Customer ID.
        """
        crowd_strike_falcon.add_entries(
            "custom_indicators",
            MOCK_DATA["iocs_entities_indicators_ids"]["resources"],
        )
        UpdateIOCInformation.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        parameters=PARAMS,
        entities=[HOSTNAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_when_cid_is_in_config(
        self,
        crowd_strike_falcon: CrowdStrikeFalcon,
        script_session: CrowdStrikeFalconSession,
    ) -> None:
        """Verifies that 'member_cid' is sent when the integration config
        contains a Customer ID.
        """
        crowd_strike_falcon.add_entries(
            "custom_indicators",
            MOCK_DATA["iocs_entities_indicators_ids"]["resources"],
        )
        UpdateIOCInformation.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
