from __future__ import annotations

import pytest

from _logger import StubLogger
from SiemplifyJob import SiemplifyJob


@pytest.fixture
def job() -> SiemplifyJob:
    """A SiemplifyJob test double.

    Mirrors tests/test_connectors/conftest.py's `connector` fixture: the bare
    stub class from tests/stubs/SiemplifyJob.py only needs to exist for
    isinstance checks; every attribute/method the job scripts and
    UtilsManager's job helpers actually call is attached here as a plain
    in-memory double.

    - `get/set_scoped_job_context_property` back both the checkpoint
      timestamp (UtilsManager.save_timestamp_for_job/get_last_success_time_for_job)
      and the OAuth token cache (TIPCommon.oauth.JobCredStorage, selected by
      VectraRUXManager because this attribute is present).
    - `get_cases_ids_by_filter`/`_get_case_by_id` back the open-case lookup;
      populate `job._cases` (case_id -> case dict, see tests/core/case.py)
      per test.
    - `close_alert` records every call in `job._closed_alerts` instead of
      actually closing anything.
    - `get_cases_by_filter` backs the case-name lookup used to pull in
      historical cases sitting outside the fetch window (see
      UtilsManager.get_open_cases_by_case_name); populate
      `job._historical_cases_by_name` (case title -> list of case dicts,
      each needing an "identifier" and "status" key - see
      tests/core/case.py's `soar_case`) per test. Every call's `case_names`
      is recorded in `job._cases_by_filter_calls`, so a test can assert the
      lookup was (or wasn't) made at all.
    """
    j = SiemplifyJob()
    j.LOGGER = StubLogger()
    j.script_name = ""
    j.parameters = {}

    j._scoped_job_context = {}
    j.get_scoped_job_context_property = (
        lambda property_key: j._scoped_job_context.get(property_key)
    )
    j.set_scoped_job_context_property = (
        lambda property_key, property_value: j._scoped_job_context.__setitem__(
            property_key, property_value,
        )
    )

    def extract_job_param(
        param_name, default_value=None, input_type=str, is_mandatory=False, print_value=True,
    ):
        value = j.parameters.get(param_name)
        if value is None:
            value = default_value
        if is_mandatory and (value is None or (isinstance(value, str) and not value.strip())):
            raise Exception(f"Mandatory parameter '{param_name}' was not provided.")
        if value is None:
            return None
        return str(value) if input_type is str else value

    j.extract_job_param = extract_job_param

    j._cases = {}
    j.get_cases_ids_by_filter = lambda **kwargs: list(j._cases.keys())
    j._get_case_by_id = lambda case_id: j._cases[case_id]

    j._closed_alerts = []
    j.close_alert = (
        lambda root_cause, comment, reason, case_id, alert_id=None: j._closed_alerts.append(
            {
                "root_cause": root_cause,
                "comment": comment,
                "reason": reason,
                "case_id": case_id,
                "alert_id": alert_id,
            },
        )
    )

    j._historical_cases_by_name = {}
    j._cases_by_filter_calls = []

    def get_cases_by_filter(case_names=None, statuses=None, environments=None, **kwargs):
        j._cases_by_filter_calls.append(case_names)
        return [
            case
            for name in (case_names or [])
            for case in j._historical_cases_by_name.get(name, [])
        ]

    j.get_cases_by_filter = get_cases_by_filter

    j._ended = False
    j.end_script = lambda: setattr(j, "_ended", True)

    return j


def run_job(job_module, job_execution, parameters):
    """Runs a job module's `main()` with the given parameters against the
    provided (already-configured) test double.
    """
    job_execution.parameters = parameters

    original = job_module.SiemplifyJob
    job_module.SiemplifyJob = lambda: job_execution
    try:
        job_module.main()
    finally:
        job_module.SiemplifyJob = original
