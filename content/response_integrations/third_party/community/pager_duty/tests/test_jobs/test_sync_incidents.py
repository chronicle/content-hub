from __future__ import annotations

from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession


def test_map_product_data_to_case_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_map,
) -> None:
    """Tests mapping product data to case successfully."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "resolved", "incident_key": "key1"}]
    })

    job.map_product_data_to_case(job_case_map)

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path.endswith("/incidents/P123")
    assert "alert_1" in job_case_map.alert_metadata
    assert job_case_map.alert_metadata["alert_1"].status == "resolved"


def test_map_product_data_to_case_not_found_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_map,
) -> None:
    """Tests mapping product data to case when incident is not found."""
    job.map_product_data_to_case(job_case_map)

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path.endswith("/incidents/P123")
    assert "alert_1" not in job_case_map.alert_metadata


def test_sync_status_soar_to_pagerduty_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync,
) -> None:
    """Tests syncing status from SOAR to PagerDuty successfully."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "triggered", "incident_key": "key1"}]
    })

    job.sync_status(job_case_sync)

    assert len(script_session.request_history) == 2
    assert script_session.request_history[0].request.url.path.endswith("/incidents/P123/notes")
    assert script_session.request_history[1].request.url.path.endswith("/incidents/P123")

    incident = pagerduty.get_incident("P123")
    assert incident["status"] == "resolved"


def test_sync_status_pagerduty_to_soar_close_case_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync_close_case,
) -> None:
    """Tests syncing status from PagerDuty to SOAR resulting in closing the case."""
    job.sync_status(job_case_sync_close_case)

    assert job.soar_job.close_case.called


def test_sync_status_pagerduty_to_soar_close_alert_success(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job,
    job_case_sync_close_alert,
) -> None:
    """Tests syncing status from PagerDuty to SOAR resulting in closing only the alert."""
    job.sync_status(job_case_sync_close_alert)

    assert job.soar_job.close_alert.called
    assert not job.soar_job.close_case.called


def test_sync_status_soar_to_pagerduty_failure(
    script_session: PagerDutySession,
    pagerduty: PagerDuty,
    job_failing_api,
    job_case_sync,
) -> None:
    """Tests syncing status from SOAR to PagerDuty with API failure handling."""
    pagerduty.set_incidents({
        "incidents": [{"id": "P123", "status": "triggered", "incident_key": "key1"}]
    })

    job_failing_api.sync_status(job_case_sync)

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path.endswith("/incidents/P123/notes")
    assert job_failing_api.logger.error.called
