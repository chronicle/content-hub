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
    CrowdStrikeStreamingConnector,
)
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run

from crowd_strike_falcon.tests.common import (
    INTEGRATION_PATH,
    create_stream_detection,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
    CrowdStrikeFalcon,
)
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import AUTH_ROUTE
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

IDS_DB_KEY: str = "offset"
DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH
    / 'connectors'
    / "CrowdStrikeStreamingConnector.yaml"
)
DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "alert_type",
    "EventClassId": "event_type",
    "API Root": "https://api.crowdstrike.com",
    "Client ID": "38c5488700bd4741a75ba6a965843a9b",
    "Client Secret": "1YzgGK9IoZcFPLVDOwh8pseCuWE7it25a34Mx06R",
    "Disable Overflow": True,
    "Max Day Backwards": 100,
    "Max Events per Cycle": 100,
    "Min Severity": 10,
    "Verify SSL": True,
    "Use dynamic list as a blocklist": True,
}

NAME: str = "CrowdStrike 26334507-logged"
DETECTION_ID: str = "2a1c5ef609ac479ba77f8ca5879c82fc"
ALERT_ROUTE: str = "/sensors/entities/datafeed/v2"

CONNECTOR_CUSTOMER_ID = "connector_cid_streaming_202"
PARAMETERS_WITH_CID = DEFAULT_PARAMETERS.copy()
PARAMETERS_WITH_CID["Customer ID"] = CONNECTOR_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestTestRun:
    """Tests connector behavior during a test run."""

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_streaming_connector_run(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        connector_output: MockConnectorOutput,
    ) -> None:
        """Verifies that the connector fetches and processes alerts correctly."""
        crowd_strike_falcon.add_stream_detection(
            create_stream_detection(DETECTION_ID).raw_data,
        )

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeStreamingConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == ALERT_ROUTE
        assert connector_output.results.json_output.alerts[0].name == NAME

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_streaming_connector_does_not_save_to_external_context(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        """Verifies that during a test run, no data is saved to external context."""
        crowd_strike_falcon.add_stream_detection(
            create_stream_detection(DETECTION_ID).raw_data,
        )

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeStreamingConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == ALERT_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1

        row_key: ExternalContextRowKey = ExternalContextRowKey(
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
    def test_streaming_connector_run_with_stream(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        """Verifies that alert offsets are saved to external context."""
        crowd_strike_falcon.add_stream_detection(
            create_stream_detection(DETECTION_ID).raw_data,
        )

        set_is_test_run_to_false()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeStreamingConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == ALERT_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1

        ids: list[str] = external_context.get_loaded_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert len(ids) == 1


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
        crowd_strike_falcon.add_stream_detection(
            create_stream_detection(DETECTION_ID).raw_data,
        )

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeStreamingConnector.main(is_test)

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == CONNECTOR_CUSTOMER_ID
