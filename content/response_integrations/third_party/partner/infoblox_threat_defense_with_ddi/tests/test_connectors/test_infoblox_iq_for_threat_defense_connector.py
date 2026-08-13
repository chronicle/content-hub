from __future__ import annotations

import pathlib

from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

from ..common import INTEGRATION_PATH, load_connector
from ..core.product import Infoblox
from ..core.session import InfobloxSession

IQForThreatDefenseConnector = load_connector("Infoblox - IQ for Threat Defense Connector")

DEF_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "connectors", "Infoblox - IQ for Threat Defense Connector.yaml")

DEFAULT_PARAMETERS = {
    "API Root": "https://csp.infoblox.test",
    "API Key": "test-api-key",
    "Verify SSL": "false",
    "PythonProcessTimeout": "30",
    "EventClassId": "name",
    "DeviceProductField": "Infoblox Threat Defense with DDI",
    "Environment Field Name": "Default Environment",
    "Environment Regex Pattern": ".*",
}

INSIGHT = {
    "insight_id": "insight-1",
    "name": "Insight One",
    "description": "desc",
    "severity": "High",
    "status": "Needs Review",
    "evaluation_start_date": "2025-01-01T00:00:00.000Z",
    "evaluation_end_date": "2025-01-02T00:00:00.000Z",
}


class TestIQForThreatDefenseConnector:
    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_creates_alert_for_new_insight(
        self,
        script_session: InfobloxSession,
        connector_output: MockConnectorOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_insights_list_response({"insight_list": [INSIGHT]})

        IQForThreatDefenseConnector.main(True)

        alerts = connector_output.results.json_output.alerts
        assert len(alerts) == 1
        assert alerts[0].name == "Insight One"

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_no_insights_produces_no_alerts(
        self,
        script_session: InfobloxSession,
        connector_output: MockConnectorOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_insights_list_response({"insight_list": []})

        IQForThreatDefenseConnector.main(True)

        assert connector_output.results.json_output.alerts == []
