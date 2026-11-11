from __future__ import annotations

import pathlib

from TIPCommon.types import SingleJson

from google_threat_intelligence.connectors import livehunt_connector
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.common import INTEGRATION_PATH

from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' / "livehunt_connector.yaml"
)

DEFAULT_PARAMETERS: SingleJson = {
    "API Root": "https://www.virustotal.com",
    "API Key": "the key",
    "EventClassId": "event_type",
    "DeviceProductField": "Product Name",
    "Max Notifications To Fetch": 40,
    "Max Hours Backwards": 1,
    "Verify SSL": True,
    "Use dynamic list as a blocklist": True,
    "Entity Type Filter": "file",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_livehunt_connector_default(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = livehunt_connector.LivehuntConnector("LivehuntFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path == "/api/v3/ioc_stream"
    params = request.kwargs.get("params", {})
    assert "filter" in params
    assert "(entity_type:file)" in params["filter"]


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={
        **DEFAULT_PARAMETERS,
        "Entity Type Filter": "file, url",
    },
)
def test_livehunt_connector_multiple_entity_types(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = livehunt_connector.LivehuntConnector("LivehuntFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path == "/api/v3/ioc_stream"
    params = request.kwargs.get("params", {})
    assert "filter" in params
    assert "(entity_type:file OR entity_type:url)" in params["filter"]


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters={
        **DEFAULT_PARAMETERS,
        "Entity Type Filter": "",
    },
)
def test_livehunt_connector_empty_entity_type_filter(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = livehunt_connector.LivehuntConnector("LivehuntFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path == "/api/v3/ioc_stream"
    params = request.kwargs.get("params", {})
    assert "filter" in params
    assert "entity_type" not in params["filter"]
