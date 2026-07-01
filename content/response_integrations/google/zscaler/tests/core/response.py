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
import pathlib

import json

from requests.exceptions import HTTPError


class MockResponse:
    """
    A mock object simulating the requests.Response.
    """

    def __init__(
        self,
        status_code: int,
        json_data: dict | list | None = None,
        text_data: str | None = None,
    ) -> None:
        self.status_code: int = status_code
        self._json_data: dict | list | None = json_data
        self._text_data: str | None = text_data

    def json(self) -> dict | list | None:
        """Returns the JSON data."""
        if self._json_data is not None:
            return self._json_data
        if self._text_data is not None:
            return json.loads(self._text_data)
        return None

    def raise_for_status(self) -> None:
        """Raises an HTTPError if the status code is 4xx or 5xx."""
        if 400 <= self.status_code < 600:
            error = HTTPError(f"Mock HTTP Error: {self.status_code}")
            error.response = self
            raise error

    @property
    def content(self) -> bytes:
        """Returns the content as bytes."""
        data: str = self._text_data or json.dumps(self._json_data)
        return data.encode("utf-8")
