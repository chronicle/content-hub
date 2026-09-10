from __future__ import annotations

import json

import pytest

from constants import PREVIOUS_ALERTS_TIMESTAMP_DB_KEY
from tests.common import load_job
from tests.core.case import cyber_alert, soar_case
from tests.test_jobs.conftest import run_job
from VectraRUXExceptions import InvalidIntegerException, VectraRUXException

JOB_NAME = "Vectra RUX - Clean Up Previous Alerts For Expired Detections Job"

DEFAULT_PARAMETERS = {
    "Max Hours Backwards": "24",
    "Environments": "Default Environment",
    "Products": "Vectra RUX",
    "Max Cases To Process": "2000",
}


class TestValidation:
    def test_rejects_non_integer_hours_backwards(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "abc"}

        with pytest.raises(InvalidIntegerException):
            run_job(job_module, job, parameters)

    def test_rejects_zero_hours_backwards(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "0"}

        with pytest.raises(VectraRUXException, match="must be greater than 0"):
            run_job(job_module, job, parameters)

    def test_rejects_negative_hours_backwards(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "-5"}

        with pytest.raises(InvalidIntegerException):
            run_job(job_module, job, parameters)

    def test_rejects_max_cases_to_process_over_ceiling(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Cases To Process": "10001"}

        with pytest.raises(VectraRUXException, match="must not exceed 10000"):
            run_job(job_module, job, parameters)

    def test_rejects_blank_environments(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Environments": " , "}

        with pytest.raises(VectraRUXException, match="cannot be empty"):
            run_job(job_module, job, parameters)

    def test_rejects_blank_products(self, job):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Products": " , "}

        with pytest.raises(VectraRUXException, match="cannot be empty"):
            run_job(job_module, job, parameters)


class TestAlertClosing:
    """Verifies the job closes every earlier alert for a detection_id once
    the most recently created alert for it is closed/expired on Vectra, per
    UtilsManager.close_previous_alerts_for_expired_detections.
    """

    def test_closes_previous_alert_when_latest_is_closed(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-old", detection_ids=[1001], creation_time=1000)],
                modification_time=5000,
            ),
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="closed",
                    ),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert [c["alert_id"] for c in job._closed_alerts] == ["alert-old"]
        assert job._closed_alerts[0]["case_id"] == "1"
        assert json.loads(job._scoped_job_context[PREVIOUS_ALERTS_TIMESTAMP_DB_KEY]) == 5001

    def test_closes_previous_alert_when_latest_is_expired(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-old", detection_ids=[1001], creation_time=1000)],
            ),
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="expired",
                    ),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert [c["alert_id"] for c in job._closed_alerts] == ["alert-old"]

    def test_does_not_close_when_latest_is_open(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-old", detection_ids=[1001], creation_time=1000)],
            ),
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="open",
                    ),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._closed_alerts == []

    def test_single_alert_for_detection_is_never_closed(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[
                    cyber_alert("alert-1", detection_ids=[1001], investigation_status="closed"),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._closed_alerts == []

    def test_ignores_alerts_from_case_with_unmatched_product(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-old", detection_ids=[1001], creation_time=1000,
                        device_product="Other Product",
                    ),
                ],
            ),
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="closed",
                    ),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)  # Products default: "Vectra RUX"

        # "alert-old" is filtered out by product, leaving only 1 alert for
        # detection 1001 - too few to have a "previous" alert to close.
        assert job._closed_alerts == []

    def test_closes_across_multiple_cases(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-1", detection_ids=[1001], creation_time=1000)],
            ),
            "2": soar_case(
                cyber_alerts=[cyber_alert("alert-2", detection_ids=[1001], creation_time=2000)],
            ),
            "3": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-3", detection_ids=[1001], creation_time=3000,
                        investigation_status="expired",
                    ),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        closed_ids = {c["alert_id"] for c in job._closed_alerts}
        assert closed_ids == {"alert-1", "alert-2"}


class TestHistoricalCases:
    """Verifies the job looks past its configured fetch window for a
    detection's other OPEN cases, by case name, once that detection's latest
    known alert already looks closed/expired - per
    UtilsManager._expand_terminal_detections_to_related_cases.
    """

    def test_closes_older_alert_found_in_historical_case_outside_window(self, job):
        job._cases = {
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="closed",
                    ),
                ],
                title="Case-1001",
            ),
        }
        job._historical_cases_by_name["Case-1001"] = [
            soar_case(
                cyber_alerts=[
                    cyber_alert("alert-old", detection_ids=[1001], creation_time=1000),
                ],
                title="Case-1001",
                identifier="1",
            ),
        ]
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert [c["alert_id"] for c in job._closed_alerts] == ["alert-old"]
        assert job._closed_alerts[0]["case_id"] == "1"

    def test_skips_historical_case_that_has_since_closed(self, job):
        job._cases = {
            "2": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-new", detection_ids=[1001], creation_time=2000,
                        investigation_status="closed",
                    ),
                ],
                title="Case-1001",
            ),
        }
        job._historical_cases_by_name["Case-1001"] = [
            soar_case(
                cyber_alerts=[
                    cyber_alert("alert-old", detection_ids=[1001], creation_time=1000),
                ],
                title="Case-1001",
                identifier="1",
                status=2,  # No longer OPEN by the time the name search runs.
            ),
        ]
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._closed_alerts == []

    def test_does_not_search_historical_cases_when_detection_is_not_terminal(self, job):
        job._cases = {
            "1": soar_case(
                cyber_alerts=[
                    cyber_alert(
                        "alert-open", detection_ids=[1001], creation_time=2000,
                        investigation_status="open",
                    ),
                ],
                title="Case-1001",
            ),
        }
        job._historical_cases_by_name["Case-1001"] = [
            soar_case(
                cyber_alerts=[
                    cyber_alert("alert-old", detection_ids=[1001], creation_time=1000),
                ],
                title="Case-1001",
                identifier="2",
            ),
        ]
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._cases_by_filter_calls == []
        assert job._closed_alerts == []
