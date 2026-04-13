from __future__ import annotations

import contextlib
import dataclasses


@dataclasses.dataclass(slots=True)
class UrlScanIo:
    _fail_requests_active: bool = False
    _submit_url_for_scan_response: dict | None = None
    _get_url_scan_report_response: dict | None = None
    _get_scan_report_by_id_response: dict | None = None
    _search_scans_response: dict | None = None

    @contextlib.contextmanager
    def fail_requests(self):
        self._fail_requests_active = True
        try:
            yield
        finally:
            self._fail_requests_active = False

    def test_connectivity(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for test_connectivity")
        return {
            "token": "mock_token_value",
            "access_token": "mock_token_value",
            "session": "mock_session",
            "userId": "mock_user",
            "expires_in": 3600,
        }

    def validate_response(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for validate_response")
        return {
            "token": "mock_token_value",
            "access_token": "mock_token_value",
            "session": "mock_session",
            "userId": "mock_user",
            "expires_in": 3600,
        }

    def set_submit_url_for_scan_response(self, response: dict) -> None:
        self._submit_url_for_scan_response = response

    def submit_url_for_scan(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for submit_url_for_scan")
        if self._submit_url_for_scan_response is not None:
            return self._submit_url_for_scan_response
        return {
            "ok": True,
            "data": {"id": "mock_id"},
            "results": [{"id": "mock_id"}],
            "result": "success",
            "success": True,
            "response_code": "1",
        }

    def set_get_url_scan_report_response(self, response: dict) -> None:
        self._get_url_scan_report_response = response

    def get_url_scan_report(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_url_scan_report")
        if self._get_url_scan_report_response is not None:
            return self._get_url_scan_report_response
        return {
            "ok": True,
            "data": {"id": "mock_id"},
            "results": [{"id": "mock_id"}],
            "result": "success",
            "success": True,
            "response_code": "1",
        }

    def set_get_scan_report_by_id_response(self, response: dict) -> None:
        self._get_scan_report_by_id_response = response

    def get_scan_report_by_id(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_scan_report_by_id")
        if self._get_scan_report_by_id_response is not None:
            return self._get_scan_report_by_id_response
        return {
            "ok": True,
            "data": {"id": "mock_id"},
            "results": [{"id": "mock_id"}],
            "result": "success",
            "success": True,
            "response_code": "1",
        }

    def set_search_scans_response(self, response: dict) -> None:
        self._search_scans_response = response

    def search_scans(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for search_scans")
        if self._search_scans_response is not None:
            return self._search_scans_response
        return {
            "ok": True,
            "data": {"id": "mock_id"},
            "results": [{"id": "mock_id"}],
            "result": "success",
            "success": True,
            "response_code": "1",
        }
