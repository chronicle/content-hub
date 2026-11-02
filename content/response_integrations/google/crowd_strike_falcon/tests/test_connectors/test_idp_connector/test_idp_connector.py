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
import sys
from typing import Any

import pytest
from crowd_strike_falcon.connectors import (
    CrowdStrikeIdentityProtectionDetectionsConnector,
)
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run

from crowd_strike_falcon.tests.common import INTEGRATION_PATH, create_alert
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import AUTH_ROUTE, IDS_DB_KEY
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH
    / 'connectors'
    / "CrowdStrikeIdentityProtectionDetectionsConnector.yaml"
)
DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "alert_type",
    "EventClassId": "event_type",
    "API Root": "https://api.crowdstrike.com",
    "Client ID": "38c5488700bd4741a75ba6a965843a9b",
    "Client Secret": "1YzgGK9IoZcFPLVDOwh8pseCuWE7it25a34Mx06R",
    "Disable Overflow": True,
    "Max Hours Backwards": 1,
    "Max Detections To Fetch": 100,
    "Lowest Severity Score To Fetch": 10,
    "Verify SSL": True,
    "Use dynamic list as a blocklist": True,
}
NAME: str = "Privilege escalation (endpoint)"
ALERT_ID: str = (
    "27fe4e476ca3490b8476b2b6650e5a74:ind:d498fc988cd34ab3b946b46cff08d88a:"
    "48661733116699-41004-7952912"
)
DETECTION_ROUTE: str = "/alerts/queries/alerts/v2"

CONNECTOR_CUSTOMER_ID = "connector_cid_idp_789"
PARAMETERS_WITH_CID = DEFAULT_PARAMETERS.copy()
PARAMETERS_WITH_CID["Customer ID"] = CONNECTOR_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestTestRun:
    """Tests connector behavior during a test run."""

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_idp_connector_run(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        connector_output: MockConnectorOutput,
    ) -> None:
        """Verifies the connector fetches and processes detections correctly."""
        crowd_strike_falcon.add_alert(create_alert(ALERT_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeIdentityProtectionDetectionsConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert connector_output.results.json_output.alerts[0].name == NAME

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_idp_connector_does_not_save_to_external_context(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        """Verifies that during a test run, no data is saved to external context."""
        crowd_strike_falcon.add_alert(create_alert(ALERT_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeIdentityProtectionDetectionsConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1

        row_key = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert row_key not in external_context


class TestConnectorExternalContext:
    """Tests the connector's interaction with external context in a normal run."""

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_idp_connector_run_with_detections(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        """Verifies that detection IDs are saved to external context."""
        crowd_strike_falcon.add_alert(create_alert(ALERT_ID).raw_data)

        set_is_test_run_to_false()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeIdentityProtectionDetectionsConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1

        ids: list[str] = external_context.get_loaded_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert len(ids) == 2


@pytest.mark.usefixtures("script_session")
class TestMemberCID:
    """Tests for multi-tenancy customer ID (CID) handling."""

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=PARAMETERS_WITH_CID)
    def test_connector_uses_customer_id_for_auth(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Tests that a provided Customer ID is used for auth as 'member_cid'."""
        crowd_strike_falcon.add_alert(create_alert(ALERT_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeIdentityProtectionDetectionsConnector.main(is_test)

        auth_request: Any = script_session.request_history[0]
        token_payload: dict[str, Any] = auth_request.request.kwargs.get("data", {})

        assert token_payload.get("member_cid") == CONNECTOR_CUSTOMER_ID
