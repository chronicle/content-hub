"""Fake Abnormal Security product for tests — holds state and serves canned responses."""

from __future__ import annotations

import contextlib
import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class Abnormal:
    """In-memory fake of the Abnormal Security backend used by AbnormalSession."""

    _threats_list_response: SingleJson | None = None
    _threat_response: SingleJson | None = None
    _threat_action_response: SingleJson | None = None
    _cases_list_response: SingleJson | None = None
    _case_response: SingleJson | None = None
    _case_action_response: SingleJson | None = None
    _search_response: SingleJson | None = None
    _remediate_response: SingleJson | None = None
    _activity_status_response: SingleJson | None = None
    _fail_requests_active: bool = False

    @contextlib.contextmanager
    def fail_requests(self):
        """Force every routed call inside the context to return a 500."""
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def set_threats_list_response(self, response: SingleJson) -> None:
        self._threats_list_response = response

    def set_threat_response(self, response: SingleJson) -> None:
        self._threat_response = response

    def set_threat_action_response(self, response: SingleJson) -> None:
        self._threat_action_response = response

    def set_cases_list_response(self, response: SingleJson) -> None:
        self._cases_list_response = response

    def set_case_response(self, response: SingleJson) -> None:
        self._case_response = response

    def set_case_action_response(self, response: SingleJson) -> None:
        self._case_action_response = response

    def set_search_response(self, response: SingleJson) -> None:
        self._search_response = response

    def set_remediate_response(self, response: SingleJson) -> None:
        self._remediate_response = response

    def set_activity_status_response(self, response: SingleJson) -> None:
        self._activity_status_response = response

    def list_threats(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for ListThreats")
        return self._threats_list_response or {"threats": [], "total": 0}

    def get_threat(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetThreat")
        if self._threat_response is None:
            raise Exception("Threat response not set. Use set_threat_response().")
        return self._threat_response

    def post_threat_action(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for PostThreatAction")
        return self._threat_action_response or {"success": True}

    def list_cases(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for ListCases")
        return self._cases_list_response or {"cases": [], "total": 0}

    def get_case(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetCase")
        if self._case_response is None:
            raise Exception("Case response not set. Use set_case_response().")
        return self._case_response

    def post_case_action(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for PostCaseAction")
        return self._case_action_response or {"success": True}

    def search_messages(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for SearchMessages")
        return self._search_response or {"messages": [], "total": 0}

    def remediate_messages(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for RemediateMessages")
        return self._remediate_response or {"activity_log_id": "test-activity-id"}

    def get_activity_status(self) -> SingleJson:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for GetActivityStatus")
        return self._activity_status_response or {"status": "success"}
