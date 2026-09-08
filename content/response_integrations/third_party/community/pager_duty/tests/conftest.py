from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest
from integration_testing.common import use_live_api
from TIPCommon.base.job.job_case import JobCase, SyncMetadata

from pager_duty.jobs.SyncIncidents import SyncIncidents

from .core.product import PagerDuty
from .core.session import PagerDutySession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def pagerduty() -> PagerDuty:
    """Fixture providing a PagerDuty mock container."""
    return PagerDuty()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    pagerduty: PagerDuty,
) -> PagerDutySession:
    """Fixture to mock PagerDuty scripts' session and view request history."""
    session: PagerDutySession = PagerDutySession(pagerduty)

    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture
def mock_job_env():
    """Fixture to mock sys.stdin for job execution."""

    class MockStdin:
        def __init__(self) -> None:
            self.buffer: io.BytesIO = io.BytesIO(b'{"parameters": {}}')

    original_stdin = sys.stdin
    sys.stdin = MockStdin()
    yield
    sys.stdin = original_stdin


@pytest.fixture
def job(mock_job_env):
    """Fixture providing a SyncIncidents job instance with mocked properties."""
    original_params = SyncIncidents.params
    original_api_client = SyncIncidents.api_client
    original_logger = SyncIncidents.logger
    original_soar_job = SyncIncidents.soar_job

    SyncIncidents.params = property(
        lambda self: MagicMock(
            api_key="test_key",
            verify_ssl=True,
            from_email="user@example.com",
            max_hours_backwards=24,
        )
    )
    mock_logger = MagicMock()

    SyncIncidents.logger = property(lambda self: mock_logger)
    mock_soar_job = MagicMock()
    mock_soar_job.get_context_property.return_value = "P99999"

    SyncIncidents.soar_job = property(lambda self: mock_soar_job)
    job_instance = SyncIncidents()

    client = job_instance._init_api_clients()
    SyncIncidents.api_client = property(lambda self: client)
    job_instance._remove_synced_entries = MagicMock()

    yield job_instance
    SyncIncidents.params = original_params
    SyncIncidents.api_client = original_api_client
    SyncIncidents.logger = original_logger
    SyncIncidents.soar_job = original_soar_job


@pytest.fixture
def job_failing_api(mock_job_env):
    """Fixture providing a SyncIncidents job instance with a failing API client."""
    original_params = SyncIncidents.params
    original_api_client = SyncIncidents.api_client
    original_logger = SyncIncidents.logger
    original_soar_job = SyncIncidents.soar_job

    SyncIncidents.params = property(
        lambda self: MagicMock(
            api_key="test_key",
            verify_ssl=True,
            from_email="user@example.com",
            max_hours_backwards=24,
        )
    )
    mock_logger = MagicMock()
    SyncIncidents.logger = property(lambda self: mock_logger)
    mock_soar_job = MagicMock()
    SyncIncidents.soar_job = property(lambda self: mock_soar_job)

    job_instance = SyncIncidents()
    client = job_instance._init_api_clients()
    client.resolve_incident = MagicMock(side_effect=Exception("API Failure"))
    client.add_incident_note = MagicMock(side_effect=Exception("API Failure"))
    SyncIncidents.api_client = property(lambda self: client)
    job_instance._remove_synced_entries = MagicMock()

    yield job_instance

    SyncIncidents.params = original_params
    SyncIncidents.api_client = original_api_client
    SyncIncidents.logger = original_logger
    SyncIncidents.soar_job = original_soar_job


@pytest.fixture
def job_failing_soar_close_alert(job):
    """Fixture providing a job instance where soar_job.close_alert fails."""
    job.soar_job.close_alert.side_effect = Exception("SecOps API Error")
    job._remove_synced_entries.reset_mock()
    return job


@pytest.fixture
def job_case_map():
    """Fixture providing a JobCase mock for mapping tests."""
    job_case = MagicMock(spec=JobCase)
    alert = MagicMock()
    alert.identifier = "alert_1"
    alert.ticket_id = "P123"
    job_case.case_detail.alerts = [alert]
    job_case.alert_metadata = {}
    job_case.product_ids_from_secops_alerts = {}
    return job_case


@pytest.fixture
def job_case_sync():
    """Fixture providing a JobCase mock for syncing status (SOAR to PagerDuty)."""
    job_case = MagicMock(spec=JobCase)
    res = MagicMock()

    alert = MagicMock()
    alert.status = "close"
    alert.closure_details = {"reason": "Malicious"}

    meta = SyncMetadata(
        status="triggered", incident_number="P123", closure_reason=None
    )

    res.incidents_to_close_in_product = [
        {
            "meta": meta,
            "alert": alert,
            "is_case_closed": False,
            "comment": "SecOps closed",
        }
    ]
    res.alerts_to_close_in_soar = []

    job_case.get_status_to_sync.return_value = res
    job_case.case_detail.id_ = 1
    job_case.case_detail.is_closed = False
    job_case.case_detail.alerts = [alert]
    job_case.product_ids_from_secops_alerts = {"P123": alert}

    return job_case


@pytest.fixture
def job_case_with_rich_comments() -> JobCase:
    """Fixture providing a JobCase mock with rich-text case comments."""
    job_case = MagicMock(spec=JobCase)
    job_case.case_comments = [
        {"comment": '!<@>@</@>#$%^&amp;*()_+} {}|":&gt;?&lt;&lt;&lt;'},
        {"comment": "<p>Another &lt;clean&gt; comment</p>"},
    ]
    return job_case


@pytest.fixture
def job_case_sync_comments():
    """Fixture providing a JobCase mock configured for comment sync."""
    job_case = MagicMock(spec=JobCase)
    alert = MagicMock()
    alert.identifier = "alert_1"
    alert.alert_group_identifier = "alert_1"
    alert.incident = MagicMock(id="P123", comments=[])

    job_case.case_detail.id_ = 1
    job_case.case_detail.is_closed = False
    job_case.case_detail.alerts = [alert]
    job_case.case_comments = [
        {"comment": '!<@>@</@>#$%^&amp;*()_+} {}|":&gt;?&lt;&lt;&lt;'}
    ]
    return job_case


@pytest.fixture
def job_comments_sync(job):
    """Fixture providing a job configured to sync rich-text comments."""
    job.processed_items = {"1": ["P123"]}
    job.get_comments_to_sync = lambda jc, **kwargs: MagicMock(
        product_comments_sync_to_case=[],
        case_comments_sync_to_product=[
            f"Google SecOps 1: {jc.case_comments[0]['comment']}"
        ],
    )
    return job


@pytest.fixture
def job_with_closure_comment(job):
    """Fixture providing a job instance with a rich-text closure comment."""
    job.get_secops_closure_comment = (
        lambda jc, req: "<p>Issue resolved with &amp; &lt;system fix&gt;</p>"
    )
    return job


@pytest.fixture
def job_case_closed():
    """Fixture providing a closed JobCase mock."""
    job_case = MagicMock(spec=JobCase)
    job_case.case_detail.id_ = 1
    job_case.case_detail.is_closed = True
    return job_case


@pytest.fixture
def job_case_sync_close_case():
    """Fixture providing a JobCase mock for syncing status (close case)."""
    job_case = MagicMock(spec=JobCase)
    res = MagicMock()

    alert = MagicMock()
    alert.identifier = "alert_1"
    alert.status = "open"

    meta = SyncMetadata(status="resolved", incident_number="P123", closure_reason=None)

    res.incidents_to_close_in_product = []
    res.alerts_to_close_in_soar = [(alert, meta)]

    job_case.get_status_to_sync.return_value = res
    job_case.case_detail.id_ = 1
    job_case.case_detail.alerts = [alert]

    return job_case


@pytest.fixture
def job_case_sync_close_alert():
    """Fixture providing a JobCase mock for syncing status (close alert only)."""
    job_case = MagicMock(spec=JobCase)
    res = MagicMock()

    alert1 = MagicMock()
    alert1.identifier = "alert_1"
    alert1.status = "open"

    alert2 = MagicMock()
    alert2.identifier = "alert_2"
    alert2.status = "open"

    meta = SyncMetadata(status="resolved", incident_number="P123", closure_reason=None)

    res.incidents_to_close_in_product = []
    res.alerts_to_close_in_soar = [(alert1, meta)]

    job_case.get_status_to_sync.return_value = res
    job_case.case_detail.id_ = 1
    job_case.case_detail.alerts = [alert1, alert2]

    return job_case


@pytest.fixture
def ticket_with_id():
    """Fixture providing an AlertCard mock with standard PagerDuty ticket_id."""
    ticket = MagicMock()
    ticket.ticket_id = "P12345"
    return ticket


@pytest.fixture
def ticket_with_context():
    """Fixture providing an AlertCard mock with UUID ticket_id and context group."""
    ticket = MagicMock()
    ticket.ticket_id = "550e8400-e29b-41d4-a716-446655440000"
    ticket.alert_group_identifier = "group_1"
    return ticket


@pytest.fixture
def job_with_fetched_case_comments(job):
    """Fixture providing a job that returns specific case comments on fetch."""
    job.soar_job.fetch_case_comments.return_value = [
        {"comment": "<p>PagerDuty:P123: Existing Note</p>"}
    ]
    return job


@pytest.fixture
def job_with_failing_fetch_comments(job):
    """Fixture providing a job where fetch_case_comments raises an exception."""
    job.soar_job.fetch_case_comments.side_effect = Exception("Fetch failed")
    return job


@pytest.fixture
def job_case_deduplication():
    """Fixture providing a JobCase using real deduplication logic."""
    job_case = MagicMock(spec=JobCase)
    alert = MagicMock()
    alert.alert_group_identifier = "alert_1"
    alert.incident = MagicMock(
        id="P123",
        comments=[
            MagicMock(message="Note 1"),
            MagicMock(message="Note 2"),
        ],
    )
    job_case.case_detail.id_ = 1
    job_case.case_detail.is_closed = False
    job_case.case_detail.alerts = [alert]
    job_case.case_comments = []

    job_case.get_comments_to_sync = (
        lambda **kw: JobCase.get_comments_to_sync(job_case, **kw)
    )
    job_case.get_case_comments_hashes = (
        lambda: JobCase.get_case_comments_hashes(job_case)
    )
    job_case.get_product_comments_hashes = (
        lambda: JobCase.get_product_comments_hashes(job_case)
    )
    job_case._generate_string_hash = (
        lambda text: JobCase._generate_string_hash(job_case, text)
    )
    job_case._collect_product_comments_to_sync_to_case = (
        lambda *args: JobCase._collect_product_comments_to_sync_to_case(
            job_case, *args
        )
    )
    job_case._collect_case_comments_to_sync_to_product = (
        lambda *args: JobCase._collect_case_comments_to_sync_to_product(
            job_case, *args
        )
    )
    job_case._is_valid_product_comment = (
        lambda c, p: JobCase._is_valid_product_comment(job_case, c, p)
    )
    job_case._is_valid_secops_comment = (
        lambda c, p: JobCase._is_valid_secops_comment(job_case, c, p)
    )
    return job_case


@pytest.fixture
def job_case_secops_deduplication(job_case_deduplication):
    """Fixture with an existing SecOps comment already in PagerDuty."""
    job_case_deduplication.case_detail.alerts[0].incident.comments = [
        MagicMock(message="Google SecOps 1: Existing analyst note"),
    ]
    return job_case_deduplication
