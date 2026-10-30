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

"""Unit tests for the CrowdStrikeFalcon Download Files From Hosts action."""
from __future__ import annotations

import copy
import datetime
from typing import Any

import pytest
from crowd_strike_falcon.actions import DownloadFilesFromHosts
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from crowd_strike_falcon.tests.common import CONFIG_PATH, MOCK_DATA
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

HOSTNAME_ENTITY_ID: str = "Siemplify"
HOSTNAME_ENTITY: Entity = create_entity(
    HOSTNAME_ENTITY_ID, EntityTypesEnum.HOST_NAME,
)
FILE_NAME_ENTITY_ID: str = "yuriy.txt"
FILE_NAME_ENTITY: Entity = create_entity(
    FILE_NAME_ENTITY_ID, EntityTypesEnum.FILE_NAME,
)
OVERWRITE: bool = True
DOWNLOAD_PATH: str = "/usr/local/google/home/narunk/Downloads/"

ACTION_CUSTOMER_ID: str = "action_cid_123"
INTEGRATION_CUSTOMER_ID: str = "integration_cid_456"

PARENT_TENANT_PARAMS: SingleJson = {
    "Customer ID": "",
    "Overwrite": OVERWRITE,
    "Download Folder Path": DOWNLOAD_PATH,
}
CHILD_TENANT_PARAMS: SingleJson = {
    "Customer ID": ACTION_CUSTOMER_ID,
    "Overwrite": OVERWRITE,
    "Download Folder Path": DOWNLOAD_PATH,
}
DEVICE_ID_PARAMS: SingleJson = {
    "Customer ID": "",
    "Overwrite": OVERWRITE,
    "Download Folder Path": DOWNLOAD_PATH,
    "Device ID": "2a1c5ef609ac479ba77f8ca5879c82fc",
}

INTEGRATION_CONFIG_WITH_CID: SingleJson = {
    "API Root": "https://api.crowdstrike.com",
    "Client API ID": "dummy",
    "Client API Secret": "dummy",
    "Verify SSL": "False",
    "Customer ID": INTEGRATION_CUSTOMER_ID,
}

SCRIPT_DEADLINE_TIME: datetime.datetime = (
    datetime.datetime.now() + datetime.timedelta(minutes=10)
)
TIMEOUT: SingleJson = {
    "execution_deadline_unix_time_ms": int(
        SCRIPT_DEADLINE_TIME.timestamp() * 1000,
    ),
}


@pytest.fixture
def setup_crowdstrike_data(crowd_strike_falcon: CrowdStrikeFalcon) -> None:
    """Prepare mock data for the CrowdStrikeFalcon instance."""
    crowd_strike_falcon.add_device(MOCK_DATA["get_devices"]["resources"][0])
    crowd_strike_falcon.add_entries(
        "login_histories",
        MOCK_DATA["get_devices_entities_online_state"]["resources"],
    )


@pytest.mark.usefixtures("script_session", "setup_crowdstrike_data")
class TestHappyPath:
    """Tests for the action's successful execution paths."""

    @set_metadata(
        parameters=DEVICE_ID_PARAMS,
        entities=[FILE_NAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_download_file_with_device_id_in_progress(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies download file action is in progress when targeting device ID."""
        DownloadFilesFromHosts.main(True)
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY, FILE_NAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_parent_tenant_auth_when_no_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies authentication targets the parent tenant if no CID is given."""
        DownloadFilesFromHosts.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert "member_cid" not in token_request_payload
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY, FILE_NAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_when_action_cid_is_provided(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies auth uses the action's CID when provided."""
        DownloadFilesFromHosts.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=PARENT_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY, FILE_NAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_child_tenant_auth_falls_back_to_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies auth uses the integration's CID if the action's is empty."""
        DownloadFilesFromHosts.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == INTEGRATION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters=CHILD_TENANT_PARAMS,
        entities=[HOSTNAME_ENTITY, FILE_NAME_ENTITY],
        integration_config=INTEGRATION_CONFIG_WITH_CID,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_action_cid_overrides_integration_cid(
        self,
        script_session: CrowdStrikeFalconSession,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies that the action's CID takes precedence over the integration's."""
        DownloadFilesFromHosts.main(True)

        history_record: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = history_record.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == ACTION_CUSTOMER_ID
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        parameters={
            **DEVICE_ID_PARAMS,
            "Device ID": "non_existent_device_id",
        },
        entities=[FILE_NAME_ENTITY],
        integration_config_file_path=CONFIG_PATH,
        input_context=copy.deepcopy(TIMEOUT),
    )
    def test_download_file_device_not_found(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Verifies download file action completes immediately if no devices are found."""
        DownloadFilesFromHosts.main(True)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "Action wasn't able to create sessions for provided endpoints" in action_output.results.output_message
