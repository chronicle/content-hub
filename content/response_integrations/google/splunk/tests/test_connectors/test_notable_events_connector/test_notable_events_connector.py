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

import pathlib
import sys

from TIPCommon.consts import IDS_DB_KEY
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.utils import is_test_run

from ....connectors import SplunkNotableEventsConnector
from ....core.datamodels import NotableEvent
from ....tests.common import create_notable_event
from ....tests.core.product import Splunk
from ....tests.core.session import SplunkSession
from ....tests.test_connectors.common import CONNECTORS_DEF_PATH
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_splunk_notable_events_connector.json"
EVENT_IDS: list[str] = ["1", "2", "3"]
ENDPOINT: str = "/:/services/search/v2/jobs/export"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    external_context=MockExternalContext(),
    parameters={
        "Server Address": "http:://xyz:8089",
        "Verify SSL": True,
        "Lowest Urgency To Fetch": "AHH",
        # This is a string due to bug in TIPCommon.extraction.extract_script_param
        "Use whitelist as a blacklist": "False",
        "Username": "Test",
        "Password": "Automation",
    },
)
def test_connector_ingests_alert(
        splunk: Splunk,
        script_session: SplunkSession,
        connector_output: MockConnectorOutput,
        external_context: MockExternalContext,
) -> None:
    events: list[NotableEvent] = [create_notable_event(id_) for id_ in EVENT_IDS]
    splunk.add_notable_events(events)

    set_is_test_run_to_false()
    test_run: bool = is_test_run(sys.argv)
    SplunkNotableEventsConnector.main(test_run)

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.real_url == ENDPOINT
    assert len(connector_output.results.json_output.alerts) == len(EVENT_IDS)

    alert_ids: str = external_context.get_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        property_key=IDS_DB_KEY,
        identifier=None,
    )
    import json
    assert json.loads(alert_ids) == EVENT_IDS
