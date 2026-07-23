from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Any, Dict, List

import pytest

JOB_FILE = (
    pathlib
    .Path(__file__)
    .parents[2]
    .joinpath("jobs", "close_duplicate_violation_alerts_job.py")
)


def _load_job_module() -> ModuleType:
    """Load the job script as a module."""
    module_name = "rubrik_security_cloud.jobs.close_duplicate_violation_alerts_job"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, JOB_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load job module from {JOB_FILE}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def _rubrik_alert(series_id: str, event_name: str) -> Dict[str, Any]:
    """Build a cyber-alert carrying an RSC violation status event."""
    return {
        "identifier": f"alert-{series_id}",
        "rule_generator": "Rubrik",
        "creation_time": 1_700_000_000_000,
        "security_events": [
            {
                "additional_properties": {
                    "custom_details.eventName": event_name,
                    "custom_details.seriesId": series_id,
                }
            }
        ],
    }


class _FakeLogger:
    def info(self, *_: Any, **__: Any) -> None: ...
    def error(self, *_: Any, **__: Any) -> None: ...
    def exception(self, *_: Any, **__: Any) -> None: ...


class _FakeSiemplifyJob:
    def __init__(self, params: Dict[str, Any], cases: Dict[str, Dict[str, Any]]) -> None:
        self.LOGGER = _FakeLogger()
        self.script_name = ""
        self._params = params
        self._cases = cases
        self.closed_cases: List[str] = []
        self.comments: List[str] = []
        self.ended = False

    def extract_job_param(self, param_name, default_value=None, **__):
        return self._params.get(param_name, default_value)

    def get_cases_ids_by_filter(self, *_: Any, **__: Any) -> List[str]:
        return list(self._cases.keys())

    def _get_case_by_id(self, case_id: str) -> Dict[str, Any]:
        return self._cases[str(case_id)]

    def add_comment(self, comment: str, case_id: str, alert_identifier: str) -> None:
        self.comments.append(case_id)

    def close_case(self, *, case_id: str, **__: Any) -> None:
        self.closed_cases.append(str(case_id))

    def end(self, *_: Any, **__: Any) -> None:
        self.ended = True


BASE_PARAMS: Dict[str, Any] = {
    "Rule Generator": "",
    "Max Cases To Process": 2000,
    "Lookback Days": 7,
    "Dry Run": False,
    "Close Root Cause": "Normal behavior",
    "Close Reason": "Not Malicious",
    "Comment Prefix": "[Rubrik Dedup]",
}


@pytest.fixture
def job_module() -> ModuleType:
    return _load_job_module()


def _patch_job(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    params: Dict[str, Any],
    cases: Dict[str, Dict[str, Any]],
) -> _FakeSiemplifyJob:
    fake = _FakeSiemplifyJob(params, cases)
    monkeypatch.setattr(module, "SiemplifyJob", lambda *_, **__: fake)
    return fake


class TestCloseDuplicateViolationAlertsJob:
    def test_closes_case_with_terminal_violation(
        self, job_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cases = {
            "1": {
                "status": 1,
                "creation_time": 1_700_000_000_000,
                "cyber_alerts": [_rubrik_alert("series-1", "HighSeverityDataViolationRemediated")],
            }
        }
        fake = _patch_job(monkeypatch, job_module, dict(BASE_PARAMS), cases)

        job_module.main()

        assert fake.closed_cases == ["1"]
        assert fake.ended is True

    def test_dry_run_does_not_close_case(
        self, job_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cases = {
            "1": {
                "status": 1,
                "creation_time": 1_700_000_000_000,
                "cyber_alerts": [_rubrik_alert("series-1", "HighSeverityDataViolationDismissed")],
            }
        }
        params = dict(BASE_PARAMS)
        params["Dry Run"] = True
        fake = _patch_job(monkeypatch, job_module, params, cases)

        job_module.main()

        assert fake.closed_cases == []
        assert fake.ended is True

    def test_non_terminal_violation_left_open(
        self, job_module: ModuleType, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cases = {
            "1": {
                "status": 1,
                "creation_time": 1_700_000_000_000,
                "cyber_alerts": [_rubrik_alert("series-1", "HighSeverityDataViolationInProgress")],
            }
        }
        fake = _patch_job(monkeypatch, job_module, dict(BASE_PARAMS), cases)

        job_module.main()

        assert fake.closed_cases == []
        assert fake.ended is True
