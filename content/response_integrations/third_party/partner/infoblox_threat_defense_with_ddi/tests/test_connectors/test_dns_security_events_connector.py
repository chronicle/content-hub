from __future__ import annotations

import pathlib

from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

from ..common import INTEGRATION_PATH, load_connector
from ..core.product import Infoblox
from ..core.session import InfobloxSession

DNSSecurityEventsConnector = load_connector("Infoblox - DNS Security Events Connector")

DEF_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "connectors", "Infoblox - DNS Security Events Connector.yaml")

DEFAULT_PARAMETERS = {
    "API Root": "https://csp.infoblox.test",
    "API Key": "test-api-key",
    "Verify SSL": "false",
    "Max Hours Backwards": "24",
    "Limit": "100",
    "PythonProcessTimeout": "300",
    "EventClassId": "tclass",
    "DeviceProductField": "Infoblox Threat Defense with DDI",
    "Environment Field Name": "Default Environment",
    "Environment Regex Pattern": ".*",
}

DNS_EVENT = {
    "event_time": "2025-01-01T00:00:00.000Z",
    "qname": "evil.example.com",
    "device": "device1",
    "network": "corp-net",
    "tclass": "Malware",
    "tfamily": "Trojan",
    "threat_indicator": "evil.example.com",
    "feed_name": "feed1",
    "policy_action": "Block",
    "policy_name": "default-policy",
    "severity": "HIGH",
}


class TestDNSSecurityEventsConnector:
    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_creates_alert_for_new_event(
        self,
        script_session: InfobloxSession,
        connector_output: MockConnectorOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dns_events_page_response({"result": [DNS_EVENT]})

        DNSSecurityEventsConnector.main(True)

        alerts = connector_output.results.json_output.alerts
        assert len(alerts) == 1
        assert alerts[0].name == "Malware - evil.example.com"

    @set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
    def test_no_events_produces_no_alerts(
        self,
        script_session: InfobloxSession,
        connector_output: MockConnectorOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_dns_events_page_response({"result": []})

        DNSSecurityEventsConnector.main(True)

        assert connector_output.results.json_output.alerts == []
