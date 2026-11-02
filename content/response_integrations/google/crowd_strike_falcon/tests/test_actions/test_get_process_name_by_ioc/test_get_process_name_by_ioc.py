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

"""Tests for the GetProcessNameByIOC action in CrowdStrike Falcon."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from crowd_strike_falcon.actions import GetProcessNameByIOC
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.set_meta import set_metadata

FILEHASH_ENTITY_ID: str = "d41d8cd98f00b204e9800998ecf8427e"
FILEHASH_ENTITY: Entity = create_entity(FILEHASH_ENTITY_ID, EntityTypesEnum.FILE_HASH)
DEVICE_NAME: str = "npatni-sysops"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_606"

SUCCESS_PARAMS: SingleJson = {"Devices Names": DEVICE_NAME}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

process_data = copy.deepcopy(MOCK_DATA["alert_default"]["resources"][0])
process_data["file_name"] = process_data.get("filepath")


@pytest.mark.usefixtures("script_session")
class TestHappyPath:
    """Tests the happy path scenarios for the GetProcessNameByIOC action."""

    @set_metadata(
        entities=[FILEHASH_ENTITY],
        parameters=SUCCESS_PARAMS,
        integration_config_file_path=CONFIG_PATH,
    )
    def test_parent_tenant_auth_does_not_send_member_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Verify that 'member_cid' is not sent for parent tenant auth.

        When the integration is configured without a specific Customer ID,
        the authentication request should not include the 'member_cid'
        parameter, indicating authentication as a parent tenant.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
        crowd_strike_falcon.add_process(process_data)
        GetProcessNameByIOC.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert "member_cid" not in token_request_payload

    @set_metadata(
        entities=[FILEHASH_ENTITY],
        parameters=SUCCESS_PARAMS,
        integration_config=INTEGRATION_CONFIG_WITH_CID,
    )
    def test_child_tenant_auth_sends_integration_member_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Verify that 'member_cid' is sent for child tenant auth.

        When the integration is configured with a specific Customer ID,
        the authentication request should include the 'member_cid'
        parameter with the correct ID, indicating authentication as a
        child tenant.
        """
        crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
        crowd_strike_falcon.add_process(process_data)
        GetProcessNameByIOC.main()

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )
        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
