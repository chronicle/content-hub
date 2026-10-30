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
from crowd_strike_falcon.connectors import CrowdStrikeDetectionConnector
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run

from crowd_strike_falcon.tests.common import (
    INTEGRATION_PATH,
    create_detection,
)
from crowd_strike_falcon.tests.core.crowd_strike_falcon import CrowdStrikeFalcon
from crowd_strike_falcon.tests.core.session import CrowdStrikeFalconSession
from crowd_strike_falcon.tests.test_constants import (
    AUTH_ROUTE,
    IDS_DB_KEY,
)
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
    / "CrowdStrikeDetectionConnector.yaml"
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
    "Lowest Confidence Score To Fetch": 0,
}
NAME: str = "Suspicious activity"
DETECTION_ID: str = "ldt:2a1c5ef609ac479ba77f8ca5879c82fc:3700315675528"
DETECTION_ROUTE: str = "/detects/queries/detects/v1"

CONNECTOR_CUSTOMER_ID = "connector_cid_detections_456"
PARAMETERS_WITH_CID = DEFAULT_PARAMETERS.copy()
PARAMETERS_WITH_CID["Customer ID"] = CONNECTOR_CUSTOMER_ID


@pytest.mark.usefixtures("script_session")
class TestTestRun:

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_detection_connector_test_run(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
        connector_output: MockConnectorOutput,
    ) -> None:
        crowd_strike_falcon.add_detection(create_detection(DETECTION_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeDetectionConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert connector_output.results.json_output.alerts[0].name == NAME

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_detection_connector_run_with_detections_does_not_save_to_external_context(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        crowd_strike_falcon.add_detection(create_detection(DETECTION_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeDetectionConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1

        row_key: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert row_key not in external_context


class TestConnectorExternalContext:

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_detection_connector_run_with_detections(
        self,
        script_session: CrowdStrikeFalconSession,
        connector_output: MockConnectorOutput,
        crowd_strike_falcon: CrowdStrikeFalcon,
        external_context: MockExternalContext,
    ) -> None:
        crowd_strike_falcon.add_detection(create_detection(DETECTION_ID).raw_data)

        set_is_test_run_to_false()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeDetectionConnector.main(is_test)

        assert len(script_session.request_history) == 3
        assert script_session.request_history[0].request.url.path == AUTH_ROUTE
        assert script_session.request_history[1].request.url.path == DETECTION_ROUTE
        assert len(connector_output.results.json_output.alerts) == 1
        ids: list[str] = external_context.get_loaded_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert len(ids) == 1


@pytest.mark.usefixtures("script_session")
class TestMemberCID:

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=PARAMETERS_WITH_CID)
    def test_connector_uses_customer_id_for_auth(
        self,
        script_session: CrowdStrikeFalconSession,
        crowd_strike_falcon: CrowdStrikeFalcon,
    ) -> None:
        """Tests that a Customer ID is used for authentication.

        If a Customer ID is provided in the connector parameters, it is used for
        authentication by sending it as 'member_cid'.
        """
        crowd_strike_falcon.add_detection(create_detection(DETECTION_ID).raw_data)

        set_is_test_run_to_true()
        is_test: bool = is_test_run(sys.argv)
        CrowdStrikeDetectionConnector.main(is_test)

        auth_request: Any = script_session.request_history[0]
        token_request_payload: dict[str, Any] = auth_request.request.kwargs.get(
            "data", {},
        )

        assert token_request_payload.get("member_cid") == CONNECTOR_CUSTOMER_ID
