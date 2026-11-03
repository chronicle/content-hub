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

import json
import pathlib
import pytest

from TIPCommon.data_models import DatabaseContextType

from cb_cloud.core import exceptions
from cb_cloud.connectors import (
    CBCloudAlertsAndEventsBaselineConnector
)
from cb_cloud.tests.common import INTEGRATION_PATH, MOCK_DATA
from cb_cloud.tests.core.session import ApiSession
from cb_cloud.tests.core.product import Product
from cb_cloud.tests.test_utils import assert_search_alerts
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import ExternalContextRowKey
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' /
    "CBCloudAlertsAndEventsBaselineConnector.yaml"
)
DEFAULT_PARAMETERS: dict = {
    "DeviceProductField": "alert_type",
    "EventClassId": "event_type",
    "Verify SSL": True,
    "API Root": "https://defense.conferdeploy.net/api",
    "Organization Key": "orgKey",
    "API ID": "APIID",
    "API Secret Key": "APISECRET",
    "Max Alerts Per Cycle": 10,
    "Offset Time In Hours": 1,
    "Events Limit to Ingest per Alert": 25,
    "Alerts Backlog Timer": 60,
    "Max Backlog Alerts per Cycle": 10,
    "What Alert Field to use for Rule Generator": "type",
    "What Alert Field to use for Name field": "type",
}

INVALID_CREDS = DEFAULT_PARAMETERS.copy()
INVALID_CREDS["API Secret Key"] = "invalid"



class TestTestRun:
    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=INVALID_CREDS
    )
    def test_connector_test_run_invalid_creds(
            self,
            script_session: ApiSession,
    ) -> None:
        set_is_test_run_to_true()
        with pytest.raises(Exception) as excinfo:
            CBCloudAlertsAndEventsBaselineConnector.main(True)

        assert excinfo.type.__name__ == exceptions.CBCloudUnauthorizedError.__name__
        assert str(excinfo.value) == "Unauthorized. Please check given credentials."
        assert len(script_session.request_history) == 1

    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS
    )
    def test_connector_test_run_no_alerts(
            self,
            script_session: ApiSession,
            connector_output: MockConnectorOutput,
    ) -> None:
        set_is_test_run_to_true()
        CBCloudAlertsAndEventsBaselineConnector.main(True)

        assert connector_output.results.json_output.alerts == []
        assert len(script_session.request_history) == 1
        assert_search_alerts(script_session.request_history, -1)


    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_alerts(
            self,
            script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.add_alerts(MOCK_DATA["alerts"]["results"])
        set_is_test_run_to_true()
        CBCloudAlertsAndEventsBaselineConnector.main(True)

        assert len(script_session.request_history) == 2
        assert_search_alerts(script_session.request_history, -1)
        assert len(connector_output.results.json_output.alerts) == 1

        row_key: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            property_key="offense_events",
            identifier=None,
        )
        assert row_key not in external_context


class TestConnectorExternalContext:

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS
    )
    def test_connector_test_run_no_alerts(
            self,
            script_session: ApiSession,
            connector_output: MockConnectorOutput,
    ) -> None:
        set_is_test_run_to_false()
        CBCloudAlertsAndEventsBaselineConnector.main(False)

        assert connector_output.results.json_output.alerts == []
        assert len(script_session.request_history) == 1
        assert_search_alerts(script_session.request_history, -1)

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_alerts_no_events(
            self,
            script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.add_alerts(MOCK_DATA["alerts"]["results"])
        product.add_observations(MOCK_DATA["get_event_by_job_id"]["results"])
        product.add_observation_details(
            MOCK_DATA["get_detailed_events_by_job_id"]["results"]
        )
        set_is_test_run_to_false()
        CBCloudAlertsAndEventsBaselineConnector.main(False)

        assert len(script_session.request_history) == 6
        assert_search_alerts(script_session.request_history, 0)
        assert len(connector_output.results.json_output.alerts) == 3

        assert len(json.loads(external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key="offense_events",
            identifier=None,
        ))["offenses"]) == 3

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_overflow_added_to_cache(
            self,
            monkeypatch: pytest.MonkeyPatch,
            script_session: ApiSession,
            connector_output: MockConnectorOutput,
            product: Product,
            external_context: MockExternalContext,
    ) -> None:
        product.add_alerts(MOCK_DATA["alerts"]["results"])
        product.add_observations(MOCK_DATA["get_event_by_job_id"]["results"])
        product.add_observation_details(
            MOCK_DATA["get_detailed_events_by_job_id"]["results"]
        )
        set_is_test_run_to_false()
        monkeypatch.setattr(
            CBCloudAlertsAndEventsBaselineConnector,
            "is_overflowed",
            lambda *_, **__: True
        )
        CBCloudAlertsAndEventsBaselineConnector.main(False)

        assert len(script_session.request_history) == 2
        assert_search_alerts(script_session.request_history, 0)
        assert len(connector_output.results.json_output.alerts) == 0

        assert len(json.loads(external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key="offense_events",
            identifier=None,
        ))["offenses"]) == 3
