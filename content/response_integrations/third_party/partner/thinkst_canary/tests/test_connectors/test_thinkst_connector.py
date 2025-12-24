from __future__ import annotations

import json
import logging
import pathlib

import pytest
from thinkst_canary.core.constants import (
    THINKST_PRODUCT,
    THINKST_VENDOR,
)
from thinkst_canary.core.thinkst_manager import ThinkstConnectorManager
from thinkst_canary.tests.common import MOCKS_PATH

FAKE_API_KEY: str = "424d71d40253b9d9e555563b1e8f7b1025ca95a7d261642427f0a2d9906560d3"
FAKE_CONSOLE_HASH: str = "b1946ac9"
INCIDENTS_FILE: str = "incidents_1.json"


def mock_fetch_console_alerts(self, page_limit: int = 20) -> list[dict]:
    """
    Mocks the "fetch_console_alerts() function

    Instead of calling the Canary Console Api it just reads in
    incident data from file. The 'page_limit' argument is ignored
    """
    incident_json = pathlib.Path.joinpath(MOCKS_PATH, INCIDENTS_FILE)
    with open(incident_json, "r") as alert_file:
        incident_data = json.load(alert_file)

    return incident_data


class MockSiemplifyConnector:
    """
    Mock the mininmum functions used by the ThinkstConnectorManager
    """
    LOGGER = logging.getLogger(__name__)

    def set_connector_context_property(self, identifier, property_key, property_value):
        return

    def get_connector_context_property(self, identifier, property_key):
        return None

    def extract_connector_param(self, param_name, default_value):
        return default_value

    class context:
        class connector_info:
            environment = "ENV"


@pytest.fixture
def connector(monkeypatch: pytest.MonkeyPatch):
    """
    Creates a ThinkstConnectorManager instance for testing

    This includes mocking any functionality which might be needed
    """
    monkeypatch.setattr(ThinkstConnectorManager, '_fetch_console_alerts', mock_fetch_console_alerts)
    siemplify = MockSiemplifyConnector()
    connector = ThinkstConnectorManager(
        FAKE_API_KEY,
        FAKE_CONSOLE_HASH,
        siemplify,
        True,
    )
    yield connector


def test_parse_events(connector: ThinkstConnectorManager):
    """
    Check that parsing events from incidents works correctly

    It checks that the correct number of events are created for every
    incident, and that certain key fields and values are present.
    """
    incidents = connector._fetch_console_alerts()
    for index, incident in enumerate(incidents):
        description = incident.get("description", {})
        console_events = description.pop("events", [])
        alert_events = connector._parse_events(console_events, incident)

        # Check the number of events
        if console_events == []:
            assert len(alert_events) == 1
        else:
            assert len(alert_events) == len(console_events)

        # Spot check a few important fields
        for event in alert_events:
            assert event.get("DeviceProduct") == THINKST_PRODUCT
            assert event.get("DeviceVendor") == THINKST_VENDOR

            important_keys = ["AlertId", "EndTime", "StartTime", "Name",
                              "SourceType", "Event_RawJSON", "Alert_RawJSON"]
            for check_key in important_keys:
                assert check_key in event.keys(), f"'{check_key}' not in {event.keys()=}"


def test_fetch_alerts(connector: ThinkstConnectorManager):
    """
    Check that creating AlertInfo() objects works correctly

    It checks the correct number of alerts are created, and that important
    fields are set
    """
    incidents = connector._fetch_console_alerts()
    alerts = connector.fetch_alerts()
    assert len(incidents) == len(alerts)

    for alert in alerts:
        assert alert.device_product == THINKST_PRODUCT
        assert alert.device_vendor == THINKST_VENDOR
        assert alert.ticket_id is not None
        assert alert.display_id is not None
        assert alert.name is not None
