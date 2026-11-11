from __future__ import annotations

import pathlib
from datetime import datetime, timedelta

import pytest
from pytest_mock import MockerFixture
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.types import SingleJson

from google_threat_intelligence.connectors.asm_issues_connector import (
    IssuesConnector,
)
from google_threat_intelligence.tests.common import INTEGRATION_PATH
from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api.common_responses import (
    create_asm_issue,
)
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata

DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' / "asm_issues_connector.yaml"
)
TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
NOW: datetime = datetime.utcnow().replace(microsecond=0)

DEFAULT_PARAMETERS: SingleJson = {
    "API Root": "https://www.virustotal.com",
    "API Key": "the key",
    "Project Name": "my-project",
    "Active Group": "test-group-id",
    "Verify SSL": True,
    "EventClassId": "event_type",
    "DeviceProductField": "Product Name",
    "Max Hours Backwards": 1,
    "Max Issues To Fetch": 25,
    "Use dynamic list as a blocklist": True,
}
FETCH_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Project Name": "TestProject",
    "Max Hours Backwards": 240,
}
SMALL_BATCH_PARAMETERS: SingleJson = {**FETCH_PARAMETERS, "Max Issues To Fetch": 2}


def hours_ago(hours: float) -> datetime:
    return NOW - timedelta(hours=hours)


def to_unix(time: datetime) -> int:
    return convert_datetime_to_unix_time(time)


def count_search_requests(session: GoogleThreatIntelligenceSession) -> int:
    return sum(
        "/asm/search/issues/" in record.request.url.path
        for record in session.request_history
    )


@pytest.fixture(name="pinned_now")
def pin_now(mocker: MockerFixture) -> datetime:
    mocked_datetime = mocker.patch("api_manager.datetime", wraps=datetime)
    mocked_datetime.utcnow.return_value = NOW
    return NOW


def start_connector(last_success_time: datetime) -> IssuesConnector:
    """Run a scheduled (non test) connector iteration from the given timestamp"""
    connector = IssuesConnector("IssuesFakeConnector", is_test_run=False)
    connector.siemplify.save_timestamp(new_timestamp=to_unix(last_success_time))
    connector.start()
    return connector


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_asm_issues_connector_extracts_active_group():
    connector = IssuesConnector("IssuesFakeConnector")
    connector.extract_params()

    assert connector.params.auth_params.active_group == "test-group-id"
    assert connector.params.auth_params.asm_project_name == "my-project"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=FETCH_PARAMETERS,
)
def test_asm_issues_connector_fetches_issues_beyond_the_first_window(
    pinned_now: datetime,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    connector_output: MockConnectorOutput,
) -> None:
    issue_time: datetime = hours_ago(5)
    google_threat_intelligence_product.add_asm_issues(
        [create_asm_issue("issue-1", last_seen=issue_time.strftime(TIME_FORMAT))]
    )

    connector = start_connector(last_success_time=hours_ago(100))

    alerts = connector_output.results.json_output.alerts
    assert [alert.ticket_id for alert in alerts] == ["issue-1"]
    assert alerts[0].name == "Open Port"
    assert count_search_requests(script_session) == 5
    assert script_session.request_history[-1].request.url.path == (
        "/api/v3/asm/issues/issue-1"
    )
    assert script_session.request_history[-1].request.headers["PROJECT-ID"] == "123456"
    assert connector.siemplify.fetch_timestamp() == to_unix(issue_time)


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=FETCH_PARAMETERS,
)
def test_asm_issues_connector_advances_timestamp_over_empty_windows(
    pinned_now: datetime,
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    connector = start_connector(last_success_time=hours_ago(100))

    assert not connector_output.results.json_output.alerts
    assert count_search_requests(script_session) == 5
    assert connector.siemplify.fetch_timestamp() == to_unix(hours_ago(10))


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=FETCH_PARAMETERS,
)
def test_asm_issues_connector_keeps_timestamp_when_window_reaches_now(
    pinned_now: datetime,
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    last_success_time: datetime = hours_ago(3)

    connector = start_connector(last_success_time=last_success_time)

    assert not connector_output.results.json_output.alerts
    assert count_search_requests(script_session) == 1
    assert connector.siemplify.fetch_timestamp() == to_unix(last_success_time)


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=FETCH_PARAMETERS,
)
def test_asm_issues_connector_does_not_refetch_known_issues(
    pinned_now: datetime,
    script_session: GoogleThreatIntelligenceSession,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    connector_output: MockConnectorOutput,
) -> None:
    google_threat_intelligence_product.add_asm_issues(
        [create_asm_issue("issue-1", last_seen=hours_ago(99).strftime(TIME_FORMAT))]
    )
    first_run = start_connector(last_success_time=hours_ago(100))
    assert len(connector_output.results.json_output.alerts) == 1
    assert first_run.siemplify.fetch_timestamp() == to_unix(hours_ago(99))
    connector_output.flush()
    script_session.clear_record()

    second_run = IssuesConnector("IssuesFakeConnector", is_test_run=False)
    second_run.start()

    assert not connector_output.results.json_output.alerts
    assert count_search_requests(script_session) == 5
    assert second_run.siemplify.fetch_timestamp() == to_unix(hours_ago(99) + timedelta(hours=90))


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=FETCH_PARAMETERS,
)
def test_asm_issues_connector_test_run_does_not_persist_progress(
    pinned_now: datetime,
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    last_success_time: datetime = hours_ago(100)
    connector = IssuesConnector("IssuesFakeConnector", is_test_run=True)
    connector.siemplify.save_timestamp(new_timestamp=to_unix(last_success_time))

    connector.start()

    assert count_search_requests(script_session) == 5
    assert connector.siemplify.fetch_timestamp() == to_unix(last_success_time)


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=SMALL_BATCH_PARAMETERS,
)
def test_asm_issues_connector_explains_an_unchanged_timestamp(
    pinned_now: datetime,
    mocker: MockerFixture,
    google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
    connector_output: MockConnectorOutput,
) -> None:
    batch_time: str = hours_ago(99).strftime(TIME_FORMAT)
    google_threat_intelligence_product.add_asm_issues(
        [create_asm_issue(f"issue-{i}", last_seen=batch_time) for i in range(3)]
    )
    first_run = start_connector(last_success_time=hours_ago(100))
    assert len(connector_output.results.json_output.alerts) == 2
    assert first_run.siemplify.fetch_timestamp() == to_unix(hours_ago(99))
    connector_output.flush()

    second_run = IssuesConnector("IssuesFakeConnector", is_test_run=False)
    logged = mocker.spy(second_run.siemplify.LOGGER, "info")
    second_run.start()

    assert len(connector_output.results.json_output.alerts) == 1
    assert second_run.siemplify.fetch_timestamp() == to_unix(hours_ago(99))
    messages = [call.args[0] for call in logged.call_args_list]
    assert any(
        message.startswith(
            "Issues in the window: 3 (already ingested: 2, filtered out by name: 0, new: 1)."
        )
        for message in messages
    )
    assert any(
        message.startswith(
            f"The last success timestamp stays at {batch_time}: every processed issue (1) "
            "was last seen at that time."
        )
        for message in messages
    )
