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
import sys
import pathlib
import tempfile

from TIPCommon.utils import is_test_run
from TIPCommon.types import SingleJson

from ...connectors import XDRConnector
from ...tests.core.product import PaloAltoCortexXDR
from ...tests.core.session import PaloAltoCortexXDRSession
from ...tests import common
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

DEF_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_xdr_connector.json"

DEFAULT_PARAMETERS: SingleJson = {
    "Api Root": common.CONFIG.get("Api Root"),
    "Api Key ID": common.CONFIG.get("Api Key ID"),
    "Api Key": common.CONFIG.get("Api Key"),
    "Verify SSL": "false",
    "Max Days Backwards": 100,
    "Alerts Count Limit": 10,
    "Lowest Incident Severity To Fetch": "low",
    "Lowest Alert Severity To Fetch": "low",
    "Split Incident Alerts": "false",
    "Disable Overflow": "true",
    "Use dynamic list as a blocklist": "false",
    "Status Filter": "New,Under Investigation",
    "DeviceProductField": "Product Name",
    "EventClassId": "event_type",
    "Python Process Timeout": 180,
    "Script Timeout (Seconds)": 180,
}

ALERT_NAME: str = "Test incident Alert"


import copy

@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_xdr_connector(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    script_session: PaloAltoCortexXDRSession,
    connector_output: MockConnectorOutput,
) -> None:
    extra_data = copy.deepcopy(common.INCIDENT_EXTRA_DATA_INFO)
    alert_template = extra_data.alerts[0]
    alert_template.raw_data["host_name"] = "test-host-extracted"

    alert_endpoint = copy.deepcopy(alert_template)
    alert_endpoint.alert_id = "test_alert_endpoint"
    alert_endpoint.raw_data = copy.deepcopy(alert_template.raw_data)
    alert_endpoint.raw_data["alert_id"] = "test_alert_endpoint"
    alert_endpoint.raw_data["host_name"] = "test-endpoint-name-extracted"
    alert_endpoint.raw_data["endpoint_data"] = None
    alert_endpoint.raw_data["endpoint"] = {
        "endpoint_name": "test-endpoint-name-extracted"
    }

    alert_agent_fqdn = copy.deepcopy(alert_template)
    alert_agent_fqdn.alert_id = "test_alert_agent_fqdn"
    alert_agent_fqdn.raw_data = copy.deepcopy(alert_template.raw_data)
    alert_agent_fqdn.raw_data["alert_id"] = "test_alert_agent_fqdn"
    alert_agent_fqdn.raw_data["host_name"] = "test-fqdn-extracted"
    alert_agent_fqdn.raw_data["endpoint_data"] = None
    alert_agent_fqdn.raw_data["endpoint"] = None
    alert_agent_fqdn.raw_data["agent_fqdn"] = "test-fqdn-extracted"

    extra_data.alerts.extend([alert_endpoint, alert_agent_fqdn])
    extra_data.raw_data["alerts"]["data"].extend([
        alert_endpoint.raw_data,
        alert_agent_fqdn.raw_data
    ])

    palo_alto_cortex_xdr.add_incidents(common.INCIDENTS_INFO)
    palo_alto_cortex_xdr.add_incident_extra_data(extra_data)

    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)

    connector = XDRConnector.XDRConnector(is_test)
    connector.siemplify.run_folder = tempfile.gettempdir()
    connector.start()

    assert len(script_session.request_history) == 3

    assert len(connector_output.results.json_output.alerts) == 1
    alert = connector_output.results.json_output.alerts[0]
    assert alert.name == ALERT_NAME

    # Verify host_name extraction
    events = alert.events
    host_names = [event.get("host_name") for event in events if event.get("host_name")]
    assert "test-host-extracted" in host_names
    assert "test-endpoint-name-extracted" in host_names
    assert "test-fqdn-extracted" in host_names


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={**DEFAULT_PARAMETERS, "Artifacts To Ignore": "network_artifact"},
)
def test_xdr_connector_ignore_artifacts(
    palo_alto_cortex_xdr: PaloAltoCortexXDR,
    connector_output: MockConnectorOutput,
) -> None:
    palo_alto_cortex_xdr.add_incidents(common.INCIDENTS_INFO)
    palo_alto_cortex_xdr.add_incident_extra_data(common.INCIDENT_EXTRA_DATA_INFO)

    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)

    connector = XDRConnector.XDRConnector(is_test)
    connector.siemplify.run_folder = tempfile.gettempdir()
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    alert = connector_output.results.json_output.alerts[0]
    event_types = [event.get("event_type") for event in alert.events]
    assert "network_artifact" not in event_types
