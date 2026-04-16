from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

import pytest
from integration_testing.common import use_live_api

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
    from pager_duty.jobs.SyncIncidents import SyncIncidents
    
    original_params = SyncIncidents.params
    original_api_client = SyncIncidents.api_client
    original_logger = SyncIncidents.logger
    original_soar_job = SyncIncidents.soar_job
    original_sync_product_status_to_case = SyncIncidents.sync_product_status_to_case
    
    SyncIncidents.params = property(lambda self: MagicMock(api_key="test_key"))
    
    mock_logger = MagicMock()
    SyncIncidents.logger = property(lambda self: mock_logger)
    
    mock_soar_job = MagicMock()
    SyncIncidents.soar_job = property(lambda self: mock_soar_job)
    
    mock_sync_method = MagicMock()
    SyncIncidents.sync_product_status_to_case = mock_sync_method
    
    job_instance = SyncIncidents()
    client = job_instance._init_api_clients()
    SyncIncidents.api_client = property(lambda self: client)
    
    job_instance._remove_synced_entries = MagicMock()
    
    yield job_instance
    
    SyncIncidents.params = original_params
    SyncIncidents.api_client = original_api_client
    SyncIncidents.logger = original_logger
    SyncIncidents.soar_job = original_soar_job
    SyncIncidents.sync_product_status_to_case = original_sync_product_status_to_case


@pytest.fixture
def job_failing_api(mock_job_env):
    """Fixture providing a SyncIncidents job instance with a failing API client."""
    from pager_duty.jobs.SyncIncidents import SyncIncidents
    
    original_params = SyncIncidents.params
    original_api_client = SyncIncidents.api_client
    original_logger = SyncIncidents.logger
    original_soar_job = SyncIncidents.soar_job
    original_sync_product_status_to_case = SyncIncidents.sync_product_status_to_case
    
    SyncIncidents.params = property(lambda self: MagicMock(api_key="test_key"))
    
    mock_logger = MagicMock()
    SyncIncidents.logger = property(lambda self: mock_logger)
    
    mock_soar_job = MagicMock()
    SyncIncidents.soar_job = property(lambda self: mock_soar_job)
    
    mock_sync_method = MagicMock()
    SyncIncidents.sync_product_status_to_case = mock_sync_method
    
    job_instance = SyncIncidents()
    client = job_instance._init_api_clients()
    
    client.resolve_incident = MagicMock(side_effect=Exception("API Failure"))
    
    SyncIncidents.api_client = property(lambda self: client)
    
    job_instance._remove_synced_entries = MagicMock()
    
    yield job_instance
    
    SyncIncidents.params = original_params
    SyncIncidents.api_client = original_api_client
    SyncIncidents.logger = original_logger
    SyncIncidents.soar_job = original_soar_job
    SyncIncidents.sync_product_status_to_case = original_sync_product_status_to_case


@pytest.fixture
def job_case_map():
    """Fixture providing a JobCase mock for mapping tests."""
    from TIPCommon.base.job.job_case import JobCase
    job_case = MagicMock(spec=JobCase)
    alert = MagicMock()
    alert.identifier = "alert_1"
    alert.ticket_id = "P123"
    job_case.case_detail.alerts = [alert]
    job_case.alert_metadata = {}
    return job_case


@pytest.fixture
def job_case_sync():
    """Fixture providing a JobCase mock for syncing status (SOAR to PagerDuty)."""
    from TIPCommon.base.job.job_case import JobCase, SyncMetadata
    job_case = MagicMock(spec=JobCase)
    res = MagicMock()
    
    alert = MagicMock()
    alert.status = "close"
    alert.closure_details = {"reason": "Malicious"}
    
    meta = SyncMetadata(status="triggered", incident_number="P123", closure_reason=None)
    
    res.incidents_to_close_in_product = [{"meta": meta, "alert": alert}]
    res.alerts_to_close_in_soar = []
    
    job_case.get_status_to_sync.return_value = res
    job_case.case_detail.id_ = 1
    
    return job_case


@pytest.fixture
def job_case_sync_close_case():
    """Fixture providing a JobCase mock for syncing status (PagerDuty to SOAR, close case)."""
    from TIPCommon.base.job.job_case import JobCase, SyncMetadata
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
    """Fixture providing a JobCase mock for syncing status (PagerDuty to SOAR, close alert only)."""
    from TIPCommon.base.job.job_case import JobCase, SyncMetadata
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
