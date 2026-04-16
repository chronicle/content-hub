from __future__ import annotations

import contextlib
import dataclasses


@dataclasses.dataclass(slots=True)
class Certly:
    _fail_requests_active: bool = False
    _test_connectivity_response: dict | None = None

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
        return {
            "ok": True,
            "data": {"id": "mock_id"},
            "results": [{"id": "mock_id"}],
            "result": "success",
            "success": True,
            "response_code": "1",
        }
