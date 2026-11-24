from __future__ import annotations
import json
from requests.exceptions import HTTPError


class MockResponse:
    def __init__(
        self, content: dict | list, status_code: int = 200, headers: dict | None = None
    ):
        self._content = content
        self.status_code = status_code
        self.text = json.dumps(content)
        self.headers = headers or {}

    @property
    def content(self) -> bytes:
        return json.dumps(self._content).encode("utf-8")

    def json(self) -> dict | list:
        return self._content

    def raise_for_status(self) -> None:
        if 400 <= self.status_code < 600:
            raise HTTPError(f"Mock Error: {self.status_code}")
