from __future__ import annotations

import contextlib
import dataclasses


@dataclasses.dataclass(slots=True)
class FalconSandbox:
    _fail_requests_active: bool = False
    _test_connectivity_response: dict | None = None
    _submit_file_response: dict | None = None
    _submit_file_by_url_response: dict | None = None
    _get_job_state_response: dict | None = None
    _get_report_response: dict | None = None
    _get_report_by_hash_response: dict | None = None
    _get_report_by_job_id_response: dict | None = None
    _get_scan_info_multiple_scans_response: dict | None = None
    _get_scan_info_single_scan_response: dict | None = None
    _get_child_scan_info_response: dict | None = None
    _search_response: dict | None = None

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

    def set_submit_file_response(self, response: dict) -> None:
        self._submit_file_response = response

    def submit_file(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for submit_file")
        if self._submit_file_response is not None:
            return self._submit_file_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_submit_file_by_url_response(self, response: dict) -> None:
        self._submit_file_by_url_response = response

    def submit_file_by_url(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for submit_file_by_url")
        if self._submit_file_by_url_response is not None:
            return self._submit_file_by_url_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_job_state_response(self, response: dict) -> None:
        self._get_job_state_response = response

    def get_job_state(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_job_state")
        if self._get_job_state_response is not None:
            return self._get_job_state_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_report_response(self, response: dict) -> None:
        self._get_report_response = response

    def get_report(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_report")
        if self._get_report_response is not None:
            return self._get_report_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_report_by_hash_response(self, response: dict) -> None:
        self._get_report_by_hash_response = response

    def get_report_by_hash(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_report_by_hash")
        if self._get_report_by_hash_response is not None:
            return self._get_report_by_hash_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_report_by_job_id_response(self, response: dict) -> None:
        self._get_report_by_job_id_response = response

    def get_report_by_job_id(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_report_by_job_id")
        if self._get_report_by_job_id_response is not None:
            return self._get_report_by_job_id_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_scan_info_multiple_scans_response(self, response: dict) -> None:
        self._get_scan_info_multiple_scans_response = response

    def get_scan_info_multiple_scans(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_scan_info_multiple_scans")
        if self._get_scan_info_multiple_scans_response is not None:
            return self._get_scan_info_multiple_scans_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_scan_info_single_scan_response(self, response: dict) -> None:
        self._get_scan_info_single_scan_response = response

    def get_scan_info_single_scan(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_scan_info_single_scan")
        if self._get_scan_info_single_scan_response is not None:
            return self._get_scan_info_single_scan_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_get_child_scan_info_response(self, response: dict) -> None:
        self._get_child_scan_info_response = response

    def get_child_scan_info(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for get_child_scan_info")
        if self._get_child_scan_info_response is not None:
            return self._get_child_scan_info_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}

    def set_search_response(self, response: dict) -> None:
        self._search_response = response

    def search(self, *args, **kwargs) -> dict:
        if self._fail_requests_active:
            raise Exception("Simulated API failure for search")
        if self._search_response is not None:
            return self._search_response
        return {"ok": True, "data": {"id": "mock_id"}, "results": [{"id": "mock_id"}], "result": "success", "success": True, "response_code": "1"}
