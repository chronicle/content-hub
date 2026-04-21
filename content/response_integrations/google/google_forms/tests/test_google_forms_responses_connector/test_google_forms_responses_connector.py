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
import json

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.consts import IDS_DB_KEY

from google_forms.connectors import (
    GoogleFormsResponsesConnector,
)

from google_forms.tests.common import (
    DEFAULT_SA,
    INTEGRATION_PATH,
)
from google_forms.tests.core.session import GoogleFormsSession
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / "Connectors" / "GoogleFormsResponsesConnector.yaml"
)
DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "Product Name",
    "EventClassId": "event_type",
    "Delegated Email": "abc@smplylab.com",
    "Service Account JSON": DEFAULT_SA,
    "Form IDs To Track": "abcdef",
    "Alert Severity": "Low",
    "Max Hours Backwards": 1,
    "Max Responses To Fetch": 10,
    "Disable Overflow": False,
    "Verify SSL": True,
}


class TestTestRun:

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_connector_test_run_one_response(
        self,
        script_session: GoogleFormsSession,
        connector_output: MockConnectorOutput,
    ) -> None:
        set_is_test_run_to_true()

        connector = GoogleFormsResponsesConnector.ResponseConnector()
        connector.start()

        assert len(script_session.request_history) == 3
        assert (
            script_session.request_history[0].request.url.path
            == "/v1/forms/abcdef/responses"
        )
        assert script_session.request_history[1].request.url.path == "/v1/forms/abcdef"
        assert len(connector_output.results.json_output.alerts) == 1

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_response_no_context(
        self,
        script_session: GoogleFormsSession,
        connector_output: MockConnectorOutput,
        external_context: MockExternalContext,
    ) -> None:
        set_is_test_run_to_true()
        connector = GoogleFormsResponsesConnector.ResponseConnector()
        connector.start()

        assert len(script_session.request_history) == 3

        assert len(connector_output.results.json_output.alerts) == 1

        row_key: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert row_key not in external_context

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_run_with_context_ids(
        self,
        script_session: GoogleFormsSession,
        connector_output: MockConnectorOutput,
        external_context: MockExternalContext,
    ) -> None:
        set_is_test_run_to_false()
        connector = GoogleFormsResponsesConnector.ResponseConnector()
        connector.siemplify.context.connector_info.identifier = "connector_identifier"
        connector.start()

        assert len(script_session.request_history) == 3

        assert len(connector_output.results.json_output.alerts) == 1
        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            identifier="connector_identifier",
            property_key=IDS_DB_KEY,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 1
