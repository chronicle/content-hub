import json
import pathlib
import sys
from typing import Any

from dateutil.parser import parse

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, unix_now
from TIPCommon.consts import IDS_DB_KEY
from TIPCommon.data_models import DatabaseContextType
from TIPCommon.utils import is_test_run

from splunk.connectors import SplunkNotableEventsConnector
from splunk.core.datamodels import NotableEvent
from splunk.tests.common import create_notable_event
from splunk.tests.core.product import Splunk
from splunk.tests.core.session import SplunkSession
from splunk.tests.test_connectors.common import CONNECTORS_DEF_PATH
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import (
    ExternalContextRow,
    MockExternalContext,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    CONNECTORS_DEF_PATH / "SplunkNotableEventsConnector.yaml"
)
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

    alert_ids: list[str] = external_context.get_loaded_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        property_key=IDS_DB_KEY,
        identifier=None,
    )
    assert alert_ids == EVENT_IDS


@set_metadata(
    connector_def_file_path=DEF_PATH,
    external_context=MockExternalContext(
        rows=[
            ExternalContextRow(
                context_type=DatabaseContextType.CONNECTOR,
                identifier=None,
                property_key=IDS_DB_KEY,
                property_value=json.dumps(EVENT_IDS),
            )
        ]
    ),
    parameters={
        "Server Address": "http:://xyz:8089",
        "Verify SSL": True,
        "Lowest Urgency To Fetch": "AHH",
        "Use whitelist as a blacklist": "False",
        "Username": "Test",
        "Password": "Automation",
    },
)
def test_connector_advances_timestamp_when_all_alerts_already_processed(
    splunk: Splunk,
    script_session: SplunkSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    events: list[NotableEvent] = [
        create_notable_event(id_, epoch=str(i + 2)) for i, id_ in enumerate(EVENT_IDS)
    ]

    splunk.add_notable_events(events)

    external_context.set_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="timestamp",
        property_value="1000",
    )

    set_is_test_run_to_false()
    test_run: bool = is_test_run(sys.argv)
    SplunkNotableEventsConnector.main(test_run)

    assert len(connector_output.results.json_output.alerts) == 0

    saved_timestamp: str = external_context.get_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="timestamp",
    )
    assert int(saved_timestamp) == 4000


@set_metadata(
    connector_def_file_path=DEF_PATH,
    external_context=MockExternalContext(
        rows=[
            ExternalContextRow(
                context_type=DatabaseContextType.CONNECTOR,
                identifier=None,
                property_key=IDS_DB_KEY,
                property_value=json.dumps(EVENT_IDS),
            )
        ]
    ),
    parameters={
        "Server Address": "http:://xyz:8089",
        "Verify SSL": True,
        "Lowest Urgency To Fetch": "AHH",
        "Use whitelist as a blacklist": "False",
        "Username": "Test",
        "Password": "Automation",
    },
)
def test_connector_continuity_across_multiple_cycles(
    splunk: Splunk,
    script_session: SplunkSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    current_time_ms = unix_now()
    base_time_sec = int(current_time_ms / 1000)

    events: list[NotableEvent] = [
        create_notable_event(id_, epoch=str(base_time_sec - 1200 + i * 300))
        for i, id_ in enumerate(EVENT_IDS)
    ]

    splunk.add_notable_events(events)

    initial_timestamp_ms = current_time_ms - 30 * 60 * 1000
    external_context.set_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="timestamp",
        property_value=str(initial_timestamp_ms),
    )

    set_is_test_run_to_false()
    test_run: bool = is_test_run(sys.argv)
    SplunkNotableEventsConnector.main(test_run)

    assert len(connector_output.results.json_output.alerts) == 0
    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.kwargs["data"][
        "earliest_time"
    ] == int(initial_timestamp_ms / 1000)

    expected_saved_timestamp_ms_1 = (base_time_sec - 600) * 1000
    saved_timestamp: str = external_context.get_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="timestamp",
    )
    assert int(saved_timestamp) == expected_saved_timestamp_ms_1

    connector_output.flush()
    script_session.clear_record()

    splunk.add_notable_event(create_notable_event("4", epoch=str(base_time_sec - 300)))

    SplunkNotableEventsConnector.main(test_run)

    assert len(connector_output.results.json_output.alerts) == 1
    assert connector_output.results.json_output.alerts[0].ticket_id == "4"
    assert len(script_session.request_history) == 1
    assert (
        script_session.request_history[0].request.kwargs["data"]["earliest_time"]
        == base_time_sec - 600
    )

    expected_saved_timestamp_ms_2 = (base_time_sec - 300) * 1000
    saved_timestamp = external_context.get_row_value(
        context_type=DatabaseContextType.CONNECTOR,
        identifier=None,
        property_key="timestamp",
    )
    assert int(saved_timestamp) == expected_saved_timestamp_ms_2


@set_metadata(
    connector_def_file_path=DEF_PATH,
    external_context=MockExternalContext(),
    parameters={
        "Server Address": "http://xyz:8089",
        "Verify SSL": True,
        "Lowest Urgency To Fetch": "AHH",
        "Use whitelist as a blacklist": "False",
        "Username": "Test",
        "Password": "Automation",
        "Alert Start Time Field": "custom_time",
    },
)
def test_connector_custom_start_time(
    splunk: Splunk,
    script_session: SplunkSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    events: list[NotableEvent] = [create_notable_event(id_) for id_ in EVENT_IDS]
    events[0].raw_data["custom_time"] = "1622332800"
    events[1].raw_data["custom_time"] = "2026-05-30T01:09:00Z"
    events[2].raw_data["custom_time"] = "1774915200000"
    expected_end_times: list[int] = [event.get_end_time() for event in events]

    splunk.add_notable_events(events)

    set_is_test_run_to_false()
    test_run: bool = is_test_run(sys.argv)
    SplunkNotableEventsConnector.main(test_run)

    assert len(connector_output.results.json_output.alerts) == len(EVENT_IDS)
    alerts: list[AlertInfo] = connector_output.results.json_output.alerts

    assert alerts[0].start_time == 1622332800000
    assert alerts[0].end_time == expected_end_times[0]

    expected_dt_ms: int = convert_datetime_to_unix_time(parse("2026-05-30T01:09:00Z"))
    assert alerts[1].start_time == expected_dt_ms
    assert alerts[1].end_time == expected_end_times[1]

    assert alerts[2].start_time == 1774915200000
    assert alerts[2].end_time == expected_end_times[2]


@set_metadata(
    connector_def_file_path=DEF_PATH,
    external_context=MockExternalContext(),
    parameters={
        "Server Address": "http://xyz:8089",
        "Verify SSL": True,
        "Lowest Urgency To Fetch": "AHH",
        "Use whitelist as a blacklist": "False",
        "Username": "Test",
        "Password": "Automation",
        "Alert Start Time Field": "custom_time",
    },
)
def test_connector_custom_start_time_fallback(
    splunk: Splunk,
    script_session: SplunkSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    fallback_values: list[Any] = [None, "invalid_timestamp_string", "", True, "-100"]
    events: list[NotableEvent] = [
        create_notable_event(str(i)) for i in range(1, len(fallback_values) + 1)
    ]
    for event, val in zip(events, fallback_values, strict=True):
        if val is not None:
            event.raw_data["custom_time"] = val

    expected_starts = [event.get_start_time() for event in events]
    expected_ends = [event.get_end_time() for event in events]
    splunk.add_notable_events(events)

    set_is_test_run_to_false()
    SplunkNotableEventsConnector.main(is_test_run(sys.argv))

    alerts: list[AlertInfo] = connector_output.results.json_output.alerts
    assert len(alerts) == len(events)
    for alert, exp_start, exp_end in zip(
        alerts,
        expected_starts,
        expected_ends,
        strict=True,
    ):
        assert alert.start_time == exp_start
        assert alert.end_time == exp_end

