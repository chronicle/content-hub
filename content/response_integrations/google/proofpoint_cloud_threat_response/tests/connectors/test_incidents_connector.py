from __future__ import annotations

import pathlib
import sys

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run
from proofpoint_cloud_threat_response.core.constants import (
    AlertSeverityEnum,
)
from proofpoint_cloud_threat_response.connectors import (
    incidents_connector,
)
from proofpoint_cloud_threat_response.core.data_models import (
    ProofpointIncident,
)

from proofpoint_cloud_threat_response.tests.common import (
    ALERT_NAME,
    DEFAULT_INCIDENT,
    DEFAULT_QUERY,
    INTEGRATION_PATH,
    MESSAGES_JSON,
)
from proofpoint_cloud_threat_response.tests.core.product import (
    ProofpointCloudThreatResponse,
)
from proofpoint_cloud_threat_response.tests.core.session import (
    ProofpointCloudThreatResponseSession,
)
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

IDS_DB_KEY: str = "ids"
DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' / "incidents_connector.yaml"
)

DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "Product Name",
    "EventClassId": "product",
    "Environment Field Name": "product",
    "Environment Regex Pattern": ".*",
    "PythonProcessTimeout": 300,
    "API Root": "https://threatprotection-api.proofpoint.com",
    "Client ID": "123456",
    "Client Secret": "********",
    "Lowest Severity To Fetch": "",
    "Status Filter": "Open",
    "Lowest Confidence To Fetch": "",
    "Disposition Filter": "",
    "Verdict Filter": "",
    "Max Hours Backwards": 1,
    "Max Incidents To Fetch": 9,
    "Use dynamic list as a blocklist": True,
    "Disable Overflow": True,
    "Verify SSL": True,
    "Proxy Server Address": "",
    "Proxy Username": "",
    "Proxy Password": "",
}


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_incidents_connector(
    proofpoint_ctr: ProofpointCloudThreatResponse,
    script_session: ProofpointCloudThreatResponseSession,
    connector_output: MockConnectorOutput,
) -> None:
    proofpoint_ctr.add_incidents(
        DEFAULT_QUERY, [ProofpointIncident.from_json(DEFAULT_INCIDENT)]
    )
    proofpoint_ctr.add_messages(DEFAULT_INCIDENT.get("id"), [MESSAGES_JSON])

    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = incidents_connector.ProofpointCTRIncidentsConnector(is_test)
    connector.start()

    assert len(script_session.request_history) == 3
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_incidents_connector_with_no_external_context(
    proofpoint_ctr: ProofpointCloudThreatResponse,
    script_session: ProofpointCloudThreatResponseSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    proofpoint_ctr.add_incidents(
        DEFAULT_QUERY, [ProofpointIncident.from_json(DEFAULT_INCIDENT)]
    )
    proofpoint_ctr.add_messages(DEFAULT_INCIDENT.get("id"), [MESSAGES_JSON])

    set_is_test_run_to_true()
    is_test = is_test_run(sys.argv)
    connector = incidents_connector.ProofpointCTRIncidentsConnector(is_test)
    connector.start()

    assert len(script_session.request_history) == 3
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME
    assert len(connector_output.results.json_output.alerts) == 1

    row_key: ExternalContextRowKey = ExternalContextRowKey(
        context_type=DatabaseContextType.CONNECTOR,
        property_key=IDS_DB_KEY,
        identifier=None,
    )
    assert row_key not in external_context


def test_proofpoint_incident_get_priority_handles_none_and_invalid() -> None:
    # Test None priority
    incident_none = ProofpointIncident.from_json({"id": "1", "priority": None})
    assert incident_none.get_priority() == AlertSeverityEnum.LOW

    # Test missing priority key
    incident_missing = ProofpointIncident.from_json({"id": "2"})
    assert incident_missing.get_priority() == AlertSeverityEnum.LOW

    # Test invalid priority string
    incident_invalid = ProofpointIncident.from_json({"id": "3", "priority": "unknown_value"})
    assert incident_invalid.get_priority() == AlertSeverityEnum.LOW

    # Test valid priority string
    incident_high = ProofpointIncident.from_json({"id": "4", "priority": "high"})
    assert incident_high.get_priority() == AlertSeverityEnum.HIGH
