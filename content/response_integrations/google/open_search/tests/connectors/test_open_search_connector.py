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

from TIPCommon.utils import is_test_run

from open_search.connectors.open_search_connector import (
    OpenSearchConnector,
)
from open_search.tests.common import (
    INTEGRATION_PATH,
)
from open_search.tests.core.product import OpenSearchProduct
from open_search.tests.core.session import OpenSearchSession
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / "Connectors" / "open_search_connector.yaml"
)

DEFAULT_PARAMETERS = {
    "PythonProcessTimeout": 60,
    "Server Address": "https://localhost:9200",
    "Username": "",
    "Password": "",
    "JWT Token": "",
    "Authenticate": "false",
    "Verify SSL": "false",
    "CA Certificate File": "",
    "Indexes": "_all",
    "Query": "*",
    "Timestamp Field": "timestamp",
    "Alert Name Field": "event_name",
    "DeviceProductField": "device_product",
    "Environment Field": "",
    "Environment Regex Pattern": ".*",
    "Severity Field Name": "",
    "EventClassId": "name",
    "Alerts Count Limit": 10,
    "Max Days Backwards": 1,
}
ALERT_NAME: str = "Test Event"


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_opensearch_connector(
    opensearch_product: OpenSearchProduct,
    os_mock_session: OpenSearchSession,
    connector_output: MockConnectorOutput,
) -> None:
    """
    Test OpenSearch Connector
    """
    mock_search_results = {
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "failed": 0},
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_source": {
                        "device_product": "OpenSearch",
                        "event_name": "Test Event",
                        "timestamp": "2025-11-21T10:00:00Z",
                    },
                    "_id": "12345",
                }
            ],
        },
    }
    opensearch_product.set_search_results(mock_search_results)
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = OpenSearchConnector(is_test)
    connector.start()

    assert len(os_mock_session.request_history) == 1
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_opensearch_connector_with_no_external_context(
    opensearch_product: OpenSearchProduct,
    os_mock_session: OpenSearchSession,
    connector_output: MockConnectorOutput,
) -> None:
    """
    Test OpenSearch Connector with no alerts found
    """
    mock_search_results = {
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "failed": 0},
        "hits": {
            "total": {"value": 0},
            "hits": [],
        },
    }
    opensearch_product.set_search_results(mock_search_results)
    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = OpenSearchConnector(is_test)
    connector.start()

    assert len(os_mock_session.request_history) == 1
    assert not connector_output.results.json_output.alerts
