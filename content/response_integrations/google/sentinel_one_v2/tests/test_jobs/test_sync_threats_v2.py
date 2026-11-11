from __future__ import annotations

from json import JSONDecodeError
import pathlib
from unittest.mock import MagicMock, patch

from requests.exceptions import HTTPError

from TIPCommon.base.job.job_case import JobCommentsResult, JobStatusResult, SyncMetadata

from sentinel_one_v2.jobs.SyncThreatsV2 import SyncThreatsV2

from sentinel_one_v2.tests.common import MOCK_THREAT, MOCK_THREAT_FULL
from sentinel_one_v2.tests.core.product import (
    SentinelOneV2 as SentinelOneV2Product,
)
from sentinel_one_v2.tests.core.session import (
    SentinelOneV2Session,
    MockJobCase,
)
from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.set_meta import set_metadata

JOB_DEF_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent.parent
    / "Integrations"
    / "SentinelOneV2"
    / 'jobs'
    / "SyncThreatsV2.yaml"
)

JOB_DEFAULT_PARAMS = {
    "Environment Name": "Default Environment",
    "API Root": "https://mock.sentinelone.net",
    "API Token": "mock_token",
    "Max Hours Backwards": 24,
    "Verify SSL": True,
}


class MockIncident:
    """Mock representation of a SentinelOne incident to attach to soar alerts."""

    threat_id = "123456789012345678"
    incident_status = "open"


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_threats_comment_bidirection(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
    mock_job_case: MockJobCase,
) -> None:
    """Validate bidirectional comment synchronization."""
    set_is_first_run_to_true()

    threat = MOCK_THREAT.copy()
    threat["threatId"] = "123456789012345678"
    threat["threatName"] = "Comment Sync Target"

    sentinel_one_v2.add_threat("123456789012345678", threat)

    job = SyncThreatsV2()
    setattr(job.soar_job, "fetch_case_comments", lambda *args, **kwargs: [])

    case = mock_job_case("case_123456789012345678")

    case.get_comments_to_sync = lambda *args, **kwargs: JobCommentsResult(
        product_comments_sync_to_case=[],
        case_comments_sync_to_product=["SOAR Comment Test"],
    )
    case.case_detail.alerts[0].incident = MockIncident()
    setattr(job, "_get_cases_to_sync", lambda: [case])
    job.start()
    post_requests = [
        req
        for req in script_session.request_history
        if req.request.method.value == "POST"
    ]
    notes_requests = [
        req
        for req in post_requests
        if req.request.url.path == "/web/api/v2.1/threats/notes"
    ]

    assert len(notes_requests) == 1

    threat_in_product = sentinel_one_v2.threats["123456789012345678"]
    assert "notes" in threat_in_product
    assert "SOAR Comment Test" in threat_in_product["notes"]


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_status_sync(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
    mock_job_case: MockJobCase,
) -> None:
    """Scenario 2: Ensure standard status closure tracking."""
    set_is_first_run_to_true()

    threat = MOCK_THREAT.copy()
    threat["threatId"] = "123456789012345678"
    threat["threatName"] = "Status Sync Target"

    sentinel_one_v2.add_threat("123456789012345678", threat)

    job = SyncThreatsV2()
    setattr(job.soar_job, "fetch_case_comments", lambda *args, **kwargs: [])
    case = mock_job_case("case_123456789012345678")
    mock_metadata = SyncMetadata(
        status="open", severity=0, incident_id="123456789012345678"
    )
    case.get_status_to_sync = lambda *args, **kwargs: JobStatusResult(
        alerts_to_close_in_soar=[],
        incidents_to_close_in_product=[
            {"meta": mock_metadata, "reason": "True Positive", "is_case_closed": True}
        ],
    )
    setattr(job, "_get_cases_to_sync", lambda: [case])
    setattr(
        job.soar_job,
        "get_case_closure_details",
        lambda *args: [{"reason": "True Positive"}],
    )
    job.start()
    threat_in_product = sentinel_one_v2.threats["123456789012345678"]
    assert threat_in_product["incidentStatus"] == "resolved"
    post_requests = [
        req
        for req in script_session.request_history
        if req.request.method.value == "POST"
    ]
    status_requests = [
        req
        for req in post_requests
        if req.request.url.path == "/web/api/v2.1/threats/incident"
    ]
    assert len(status_requests) == 1


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_retry_handling(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
    mock_job_case: MockJobCase,
) -> None:
    """Scenario 4: Ensure retry handling processes cleanly."""
    set_is_first_run_to_true()

    threat = MOCK_THREAT.copy()
    threat["threatId"] = "123456789012345678"
    threat["threatName"] = "Retry Mock Target"

    sentinel_one_v2.add_threat("123456789012345678", threat)
    sentinel_one_v2.simulate_transient_error = True

    job = SyncThreatsV2()
    setattr(job.soar_job, "fetch_case_comments", lambda *args, **kwargs: [])

    case = mock_job_case("case_123456789012345678")
    setattr(job, "_get_cases_to_sync", lambda: [case])

    job.start()

    assert job.job_completed_successfully is True
    assert len(script_session.request_history) >= 1


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_main_execution_flow(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
    mock_job_case: MockJobCase,
) -> None:
    """Validate the standard entirely complete core main flow."""
    set_is_first_run_to_true()

    sentinel_one_v2.add_threat("123456789012345678", MOCK_THREAT_FULL)
    job = SyncThreatsV2()
    setattr(job.soar_job, "fetch_case_comments", lambda *args, **kwargs: [])

    case = mock_job_case("case_123456789012345678")
    setattr(job, "_get_cases_to_sync", lambda: [case])

    job.start()

    endpoints = [req.request.url.path for req in script_session.request_history]

    assert len(script_session.request_history) >= 1
    assert "/web/api/v2.1/threats" in endpoints
    assert "alert_1" in case.alert_metadata
    assert case.alert_metadata["alert_1"].status == "unresolved"
    assert job.job_completed_successfully is True


# pylint: disable=unused-argument,protected-access
@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_empty_content_handling(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
    mock_job_case: MockJobCase,
) -> None:
    """Scenario 6: Ensure graceful completion when zero targets are discovered."""
    set_is_first_run_to_true()

    job = SyncThreatsV2()
    setattr(job.soar_job, "fetch_case_comments", lambda *args, **kwargs: [])

    setattr(job, "_get_cases_to_sync", lambda: [])

    job.start()

    assert len(script_session.request_history) == 1
    assert (
        script_session.request_history[0].request.url.path
        == "/web/api/v2.1/agents/count"
    )
    assert job.job_completed_successfully is True
    assert getattr(job, "_get_cases_to_sync") is not None
    assert callable(getattr(job, "_get_cases_to_sync"))


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_merged_case_purges_from_processed_items(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure merged case raising JSONDecodeError logs info and is purged from state."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"100": ["123456789012345678"]}
    job.sync_limit = 10

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("100", 1000)]), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             side_effect=JSONDecodeError("Expecting value", "", 0),
         ), \
         patch.object(job.logger, "info") as mock_info, \
         patch.object(job.logger, "error") as mock_error:

        result = job._get_cases_to_sync()

        assert not result
        assert "100" not in job.processed_items
        mock_error.assert_not_called()
        mock_info.assert_any_call(
            "Could not retrieve details for case 100. Skipping."
        )


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_reassign_claimed_threats(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure _reassign_claimed_threats cleans up merged cases."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {
        "1": ["101", "102"],
        "2": ["103", "104"],
        "3": ["105"],
    }

    job._reassign_claimed_threats("1", ["101", "102", "103", "105"])

    assert job.processed_items["2"] == ["104"]
    assert "3" not in job.processed_items


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_invalid_case_details_response(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure None or invalid case details response purges case from state."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"100": ["123456789012345678"]}
    job.sync_limit = 10

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("100", 1000)]), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             return_value=None,
         ), \
         patch.object(job.logger, "info") as mock_info:

        result = job._get_cases_to_sync()

        assert not result
        assert "100" not in job.processed_items
        mock_info.assert_any_call("Could not retrieve details for case 100. Skipping.")


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_http_error_response(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure HTTPError during case overview fetch purges case from state."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"100": ["123456789012345678"]}
    job.sync_limit = 10

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("100", 1000)]), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             side_effect=HTTPError("Not found"),
         ), \
         patch.object(job.logger, "info") as mock_info:

        result = job._get_cases_to_sync()

        assert not result
        assert "100" not in job.processed_items
        mock_info.assert_any_call(
            "Could not retrieve details for case 100. Skipping."
        )


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_higher_case_id_merged_into_lower(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure higher case ID merged into lower case ID is reallocated and purged."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"3": ["101"], "4": ["102"]}
    job.sync_limit = 10

    mock_case_details = MagicMock()
    mock_case_details.id_ = 3
    mock_alert_1 = MagicMock()
    mock_alert_1.ticket_id = "101"
    mock_alert_1.alert_group_identifier = None
    mock_alert_2 = MagicMock()
    mock_alert_2.ticket_id = "102"
    mock_alert_2.alert_group_identifier = None
    mock_case_details.alerts = [mock_alert_1, mock_alert_2]

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("3", 1000)]), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             return_value=mock_case_details,
         ), \
         patch.object(job, "_is_valid_s1_id", return_value=True):

        result = job._get_cases_to_sync()

        assert len(result) == 1
        assert "4" not in job.processed_items
        assert job.processed_items["3"] == ["101", "102"]


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_merged_case_product_update_without_secops_modification(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure merged case reconciliation happens before building the threat-to-case map."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"4": ["102"], "3": ["101"]}
    job.sync_limit = 10
    job.last_run_time = 1000

    mock_case_details = MagicMock()
    mock_case_details.id_ = 3
    mock_alert_1 = MagicMock()
    mock_alert_1.ticket_id = "101"
    mock_alert_1.alert_group_identifier = None
    mock_alert_2 = MagicMock()
    mock_alert_2.ticket_id = "102"
    mock_alert_2.alert_group_identifier = None
    mock_case_details.alerts = [mock_alert_1, mock_alert_2]

    def mock_get_overview(_soar_job, case_id, **_kwargs):
        if str(case_id) == "4":
            raise JSONDecodeError("Expecting value", "", 0)
        return mock_case_details

    mock_threat_102 = MagicMock()
    mock_threat_102.threat_id = "102"

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             side_effect=mock_get_overview,
         ), \
         patch.object(job, "_is_valid_s1_id", return_value=True), \
         patch.object(
             job,
             "_get_activity_modified_threats",
             return_value=(set(), {"102": 2000}),
         ), \
         patch.object(
             job,
             "_fetch_modified_threats",
             return_value=[mock_threat_102],
         ), \
         patch.object(job, "_get_threat_modified_time_ms", return_value=2000):

        result = job._get_cases_to_sync()

        assert len(result) == 1
        assert result[0].case_detail.id_ == 3
        assert result[0].modification_time == 2000
        assert "4" not in job.processed_items
        assert job.processed_items["3"] == ["101", "102"]


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_secops_merge_into_any_case_skips_fetching_deleted_case(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure when case 8 is merged into case 9 in SecOps, deleted case 8 is never fetched."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"8": ["101"], "9": ["102"]}
    job.sync_limit = 10
    job.last_run_time = 1000

    mock_case_details = MagicMock()
    mock_case_details.id_ = 9
    mock_alert_1 = MagicMock()
    mock_alert_1.ticket_id = "101"
    mock_alert_1.alert_group_identifier = None
    mock_alert_2 = MagicMock()
    mock_alert_2.ticket_id = "102"
    mock_alert_2.alert_group_identifier = None
    mock_case_details.alerts = [mock_alert_1, mock_alert_2]

    fetched_case_ids: list[str] = []

    def mock_get_overview(_soar_job, case_id, **_kwargs):
        fetched_case_ids.append(str(case_id))
        if str(case_id) == "8":
            raise JSONDecodeError("Expecting value", "", 0)
        return mock_case_details

    mock_threat_101 = MagicMock()
    mock_threat_101.threat_id = "101"

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("9", 1500)]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             side_effect=mock_get_overview,
         ), \
         patch.object(job, "_is_valid_s1_id", return_value=True), \
         patch.object(
             job,
             "_get_activity_modified_threats",
             return_value=(set(), {"101": 2000}),
         ), \
         patch.object(
             job,
             "_fetch_modified_threats",
             return_value=[mock_threat_101],
         ), \
         patch.object(job, "_get_threat_modified_time_ms", return_value=2000):

        result = job._get_cases_to_sync()

        assert len(result) == 1
        assert result[0].case_detail.id_ == 9
        assert fetched_case_ids == ["9"]
        assert "8" not in job.processed_items
        assert job.processed_items["9"] == ["101", "102"]


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_case_without_valid_threat_ids_purged(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure a case with no valid S1 threat IDs is purged from processed_items."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {"10": ["101"]}
    job.sync_limit = 10

    mock_case_details = MagicMock()
    mock_case_details.id_ = 10
    mock_case_details.alerts = []

    with patch.object(job, "_get_case_ids_by_timestamp", return_value=[("10", 1000)]), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             return_value=mock_case_details,
         ):

        result = job._get_cases_to_sync()

        assert not result
        assert "10" not in job.processed_items


@set_metadata(job_def_file_path=JOB_DEF_PATH, parameters=JOB_DEFAULT_PARAMS)
def test_sync_threats_alert_limit_handling(
    script_session: SentinelOneV2Session,
    sentinel_one_v2: SentinelOneV2Product,
) -> None:
    """Ensure product_alerts_limit processes first oversized case and defers subsequent ones."""
    set_is_first_run_to_true()
    job = SyncThreatsV2()
    job.processed_items = {}
    job.sync_limit = 10
    job.product_alerts_limit = 1

    mock_alert_1 = MagicMock()
    mock_alert_1.ticket_id = "101"
    mock_alert_1.alert_group_identifier = None
    mock_alert_2 = MagicMock()
    mock_alert_2.ticket_id = "102"
    mock_alert_2.alert_group_identifier = None

    case_1_details = MagicMock()
    case_1_details.id_ = 1
    case_1_details.alerts = [mock_alert_1, mock_alert_2]

    case_2_details = MagicMock()
    case_2_details.id_ = 2
    case_2_details.alerts = [mock_alert_1]

    def mock_get_overview(_soar_job, case_id, **_kwargs):
        return case_1_details if str(case_id) == "1" else case_2_details

    with patch.object(
             job,
             "_get_case_ids_by_timestamp",
             return_value=[("1", 1000), ("2", 2000)],
         ), \
         patch.object(job, "modified_synced_case_ids_by_product", return_value=[]), \
         patch(
             "sentinel_one_v2.jobs.SyncThreatsV2.get_case_overview_details",
             side_effect=mock_get_overview,
         ), \
         patch.object(job, "_is_valid_s1_id", return_value=True):

        result = job._get_cases_to_sync()

        assert len(result) == 1
        assert result[0].case_detail.id_ == 1
        assert job.sorted_modified_ids == [("1", 1000)]
