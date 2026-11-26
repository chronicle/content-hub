# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
