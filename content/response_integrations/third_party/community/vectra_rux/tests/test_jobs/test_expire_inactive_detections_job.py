from __future__ import annotations

import json

import pytest

from constants import CASES_TIMESTAMP_DB_KEY
from tests.common import load_job
from tests.core.case import cyber_alert, soar_case
from tests.test_jobs.conftest import run_job
from VectraRUXExceptions import InvalidIntegerException, VectraRUXException

JOB_NAME = "Vectra RUX - Expire Inactive Detections Job"

DEFAULT_PARAMETERS = {
    "API Root": "https://test.vectra.ai",
    "Client ID": "test-client-id",
    "Client Secret": "test-client-secret",
    "Max Hours Backwards": "24",
    "Environments": "Default Environment",
    "Products": "Vectra RUX",
    "Max Detections To Fetch": "",
    "Max Cases To Process": "2000",
}


class TestValidation:
    def test_rejects_non_integer_hours_backwards(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "abc"}

        with pytest.raises(InvalidIntegerException):
            run_job(job_module, job, parameters)

    def test_rejects_zero_hours_backwards(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "0"}

        with pytest.raises(VectraRUXException, match="must be greater than 0"):
            run_job(job_module, job, parameters)

    def test_rejects_negative_hours_backwards(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Hours Backwards": "-5"}

        with pytest.raises(InvalidIntegerException):
            run_job(job_module, job, parameters)

    def test_rejects_zero_max_detections_to_fetch(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Detections To Fetch": "0"}

        with pytest.raises(InvalidIntegerException, match="Max Detections To Fetch"):
            run_job(job_module, job, parameters)

    def test_rejects_max_cases_to_process_over_ceiling(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Max Cases To Process": "10001"}

        with pytest.raises(VectraRUXException, match="must not exceed 10000"):
            run_job(job_module, job, parameters)

    def test_rejects_blank_environments(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Environments": " , "}

        with pytest.raises(VectraRUXException, match="cannot be empty"):
            run_job(job_module, job, parameters)

    def test_rejects_blank_products(self, job, mock_session, product):
        job_module = load_job(JOB_NAME)
        parameters = {**DEFAULT_PARAMETERS, "Products": " , "}

        with pytest.raises(VectraRUXException, match="cannot be empty"):
            run_job(job_module, job, parameters)


class TestAlertClosing:
    """Verifies the job closes exactly the alerts whose Vectra detection is
    inactive - and nothing else - per UtilsManager.expire_inactive_detections.
    """

    def test_closes_alert_for_inactive_detection(self, job, mock_session, product):
        product.list_detections_response = [{"id": 1001}]
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-1", detection_ids=[1001])],
                modification_time=5000,
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert [c["alert_id"] for c in job._closed_alerts] == ["alert-1"]
        assert job._closed_alerts[0]["case_id"] == "1"
        # Checkpoint should be the processed case's modification_time + 1.
        assert json.loads(job._scoped_job_context[CASES_TIMESTAMP_DB_KEY]) == 5001

    def test_does_not_close_alert_for_active_detection(self, job, mock_session, product):
        product.list_detections_response = [{"id": 1001}]
        job._cases = {
            "1": soar_case(cyber_alerts=[cyber_alert("alert-1", detection_ids=[9999])]),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._closed_alerts == []

    def test_skips_case_outside_configured_environment(self, job, mock_session, product):
        product.list_detections_response = [{"id": 1001}]
        job._cases = {
            "1": soar_case(
                cyber_alerts=[cyber_alert("alert-1", detection_ids=[1001])],
                environment="EU",
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)  # Environments default: "Default Environment"

        assert job._closed_alerts == []

    def test_skips_alert_with_unmatched_device_product(self, job, mock_session, product):
        product.list_detections_response = [{"id": 1001}]
        job._cases = {
            "1": soar_case(
                cyber_alerts=[
                    cyber_alert("alert-1", detection_ids=[1001], device_product="Other Product"),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)  # Products default: "Vectra RUX"

        assert job._closed_alerts == []

    def test_closes_only_inactive_alert_among_multiple(self, job, mock_session, product):
        product.list_detections_response = [{"id": 1001}]
        job._cases = {
            "1": soar_case(
                cyber_alerts=[
                    cyber_alert("alert-inactive", detection_ids=[1001]),
                    cyber_alert("alert-active", detection_ids=[2002]),
                ],
            ),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert [c["alert_id"] for c in job._closed_alerts] == ["alert-inactive"]

    def test_no_inactive_detections_closes_nothing(self, job, mock_session, product):
        product.list_detections_response = []
        job._cases = {
            "1": soar_case(cyber_alerts=[cyber_alert("alert-1", detection_ids=[1001])]),
        }
        job_module = load_job(JOB_NAME)

        run_job(job_module, job, DEFAULT_PARAMETERS)

        assert job._closed_alerts == []
