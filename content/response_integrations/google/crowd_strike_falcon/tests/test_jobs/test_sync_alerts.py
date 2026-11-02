# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

from crowd_strike_falcon.jobs.SyncAlerts import SyncAlerts

from integration_testing.common import set_is_first_run_to_true, set_is_first_run_to_false
from integration_testing.set_meta import set_metadata

if TYPE_CHECKING:
    from crowd_strike_falcon.tests.core.crowd_strike_falcon import (
        CrowdStrikeFalcon as CrowdStrikeFalconProduct,
    )
    from crowd_strike_falcon.tests.core.session import (
        CrowdStrikeFalconSession,
        MockJobCase,
    )

JOB_DEF_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "jobs"
    / "SyncAlerts.yaml"
)

JOB_DEFAULT_PARAMS = {
    "Environment Name": "Default Environment",
    "API Root": "https://mock.crowdstrike.com",
    "Client ID": "mock_client_id",
    "Client Secret": "mock_client_secret",
    "Max Hours Backwards": 24,
    "Verify SSL": True,
}


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_alerts_missing_alert_context(
    script_session: CrowdStrikeFalconSession,
    crowd_strike_falcon: CrowdStrikeFalconProduct,
    mock_job_case: type[MockJobCase],
) -> None:
    """Validate that when the alert context is missing,

    the job logs an error and skips the case instead of failing entirely.
    """
    set_is_first_run_to_true()

    job = SyncAlerts()
    # Avoid querying case comments from SOAR
    job.soar_job.fetch_case_comments = lambda *args, **kwargs: []

    # Create a mock job case with a missing ticketId to trigger missing context
    case = mock_job_case("case_12345", "")
    job._get_cases_to_sync = lambda: [case]

    job.start()

    # Verify the job completed successfully without throwing exceptions
    assert job.job_completed_successfully is True

    # Verify that get_alerts_details endpoint was NOT hit
    post_requests = [req for req in script_session.request_history if req.request.method.value == "POST"]
    detail_requests = [req for req in post_requests if req.request.url.path == "/alerts/entities/alerts/v2"]
    assert len(detail_requests) == 0


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_alerts_successful_execution(
    script_session: CrowdStrikeFalconSession,
    crowd_strike_falcon: CrowdStrikeFalconProduct,
    mock_job_case: type[MockJobCase],
) -> None:
    """Validate the standard successful core flow for get_alerts_details."""
    set_is_first_run_to_true()

    job = SyncAlerts()
    # Avoid querying case comments from SOAR
    job.soar_job.fetch_case_comments = lambda *args, **kwargs: []

    # Create a mock job case with a normal alert ID containing ":ind:" to be valid
    case = mock_job_case("case_12345", "valid_composite_id:ind:123")
    job._get_cases_to_sync = lambda: [case]

    job.start()

    # Verify the job completed successfully
    assert job.job_completed_successfully is True

    # Verify get_alerts_details endpoint was hit
    post_requests = [req for req in script_session.request_history if req.request.method.value == "POST"]
    detail_requests = [req for req in post_requests if req.request.url.path == "/alerts/entities/alerts/v2"]
    assert len(detail_requests) == 1
    assert detail_requests[0].response.status_code == 200


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_alerts_invalid_alert_id(
    script_session: CrowdStrikeFalconSession,
    crowd_strike_falcon: CrowdStrikeFalconProduct,
    mock_job_case: type[MockJobCase],
) -> None:
    """Validate that when the alert ID is invalid (triggers a 400 Bad Request error),

    the job handles the error gracefully, continues execution, and removes the case ID
    from processed_items.
    """
    set_is_first_run_to_true()

    job = SyncAlerts()
    job.soar_job.fetch_case_comments = lambda *args, **kwargs: []

    case = mock_job_case("case_12345", "no_ids_invalid_value")
    job._get_cases_to_sync = lambda: [case]

    job.processed_items = {"case_12345": ["no_ids_invalid_value"]}

    job.start()

    assert job.job_completed_successfully is True

    assert "case_12345" not in job.processed_items


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_alerts_multiple_context_ids(
    script_session: CrowdStrikeFalconSession,
    crowd_strike_falcon: CrowdStrikeFalconProduct,
    mock_job_case: type[MockJobCase],
) -> None:
    """Validate that when the context property contains multiple comma-separated Crowdstrike alert IDs,

    the job successfully extracts, validates, and syncs details for all of them.
    """
    set_is_first_run_to_true()

    job = SyncAlerts()
    job.soar_job.fetch_case_comments = lambda *args, **kwargs: []

    job.soar_job.get_context_property = lambda *args, **kwargs: "id1:ind:123, id2:ind:456"

    case = mock_job_case("case_12345", "de_ce69b52d-ddc4-8e35-c486-df10b1d789c4")

    case.case_detail.alerts[0].alert_group_identifier = "alert_group_1"

    job._get_cases_to_sync = lambda: [case]

    job.start()

    assert job.job_completed_successfully is True

    post_requests = [req for req in script_session.request_history if req.request.method.value == "POST"]
    detail_requests = [req for req in post_requests if req.request.url.path == "/alerts/entities/alerts/v2"]
    assert len(detail_requests) == 1
    assert detail_requests[0].response.status_code == 200

    request_json = detail_requests[0].request.kwargs.get("json")
    requested_ids = request_json.get("ids") or request_json.get("composite_ids")
    assert "id1:ind:123" in requested_ids
    assert "id2:ind:456" in requested_ids


@set_metadata(
    job_def_file_path=JOB_DEF_PATH,
    parameters=JOB_DEFAULT_PARAMS,
)
def test_sync_alerts_multiple_ids_inconclusive_closure(
    script_session: CrowdStrikeFalconSession,
    crowd_strike_falcon: CrowdStrikeFalconProduct,
    mock_job_case: type[MockJobCase],
) -> None:
    """Validate that when multiple composite IDs are mapped to a single SecOps alert card,

    and all of them are closed on the CrowdStrike side, the SecOps alert card is closed
    with reason "Inconclusive" and rootcause "Other".
    """
    from crowd_strike_falcon.core.CrowdStrikeParser import CrowdStrikeParser

    alert1 = CrowdStrikeParser.build_siemplify_alert_details({
        "id": "id1:ind:123",
        "composite_id": "id1:ind:123",
        "status": "closed",
        "severity": "high",
        "created_timestamp": "2026-06-08T18:00:00Z",
        "updated_timestamp": "2026-06-08T18:05:00Z",
    })
    alert2 = CrowdStrikeParser.build_siemplify_alert_details({
        "id": "id2:ind:456",
        "composite_id": "id2:ind:456",
        "status": "closed",
        "severity": "high",
        "created_timestamp": "2026-06-08T18:00:00Z",
        "updated_timestamp": "2026-06-08T18:05:00Z",
    })

    job = SyncAlerts()
    job.soar_job.fetch_case_comments = lambda *args, **kwargs: []
    job.soar_job.get_context_property = lambda *args, **kwargs: "id1:ind:123, id2:ind:456"

    from TIPCommon.base.job.job_case import JobCase

    case = mock_job_case("case_12345", "de_ce69b52d-ddc4-8e35-c486-df10b1d789c4")
    case.case_detail.alerts[0].status = "open"
    case.case_detail.alerts[0].alert_group_identifier = "alert_group_1"

    case.get_status_to_sync = lambda closed_status: JobCase.get_status_to_sync(case, closed_status)

    job._get_cases_to_sync = lambda: [case]
    job._fetch_product_details = lambda ids: [alert1, alert2]

    captured_calls = []
    def mock_sync_product_status_to_case(case_id, alert_id, reason, root_cause, comment):
        captured_calls.append({
            "case_id": case_id,
            "alert_id": alert_id,
            "reason": reason,
            "root_cause": root_cause,
            "comment": comment
        })

    job.sync_product_status_to_case = mock_sync_product_status_to_case

    job.start()

    assert job.job_completed_successfully is True

    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["case_id"] == 1
    assert call["reason"] == "Inconclusive"
    assert call["root_cause"] == "Other"
    assert "All crowdstrike alerts mapped with this SecOps alert are closed." in call["comment"]

