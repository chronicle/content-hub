from __future__ import annotations

import contextlib
import dataclasses


@dataclasses.dataclass(slots=True)
class Phishrod:
    _fail_requests_active: bool = False
    _test_connectivity_response: dict | None = None
    _get_incidents_response: dict | None = None
    _update_incident_response: dict | None = None
    _mark_incident_response: dict | None = None

    @contextlib.contextmanager
    def fail_requests(self):
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def set_test_connectivity_response(self, response: dict) -> None:
        self._test_connectivity_response = response

    def test_connectivity(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for test_connectivity")
        if self._test_connectivity_response is not None:
            return self._test_connectivity_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_incidents_response(self, response: dict) -> None:
        self._get_incidents_response = response

    def get_incidents(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_incidents")
        if self._get_incidents_response is not None:
            return self._get_incidents_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_update_incident_response(self, response: dict) -> None:
        self._update_incident_response = response

    def update_incident(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for update_incident")
        if self._update_incident_response is not None:
            return self._update_incident_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_mark_incident_response(self, response: dict) -> None:
        self._mark_incident_response = response

    def mark_incident(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for mark_incident")
        if self._mark_incident_response is not None:
            return self._mark_incident_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}
