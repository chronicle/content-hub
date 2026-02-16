# Copyright 2025 Google LLC
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

import io
import json
from typing import TYPE_CHECKING

import requests
from TIPCommon.utils import none_to_default_value

if TYPE_CHECKING:
    from TIPCommon.types import JSON, JsonString, SingleJson


class MockResponse(requests.Response):
    def __init__(
        self,
        content: str | JsonString | JSON = "",
        status_code: int = 200,
        encoding: str = "UTF-8",
        headers: SingleJson | None = None,
    ) -> None:
        """Initialize the response."""
        super().__init__()
        self._content: bytes = _stringify_content(content).encode(encoding)
        self.status_code: int = status_code
        self.encoding: str = encoding
        self.headers: SingleJson = none_to_default_value(headers, {})
        self.raw: io.StringIO = io.StringIO()

        self.raw.write(self.text)

    def __repr__(self) -> str:
        """Return a string representation of the object.

        Returns:
            A string representation of the MockResponse object.

        """
        return (
            f"{MockResponse.__name__}("
            f"status_code={self.status_code}, "
            f"content={self.content}, "
            f"encoding={self.encoding}, "
            f"headers={self.headers}"
            ")"
        )


def _stringify_content(content: JSON | JsonString | str) -> JsonString:
    if not isinstance(content, str):
        return json.dumps(content)

    return content
