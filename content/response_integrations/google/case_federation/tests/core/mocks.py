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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class MockHttpClient:
    """Mock replacement for the `AuthorizedSession` http client.

    Records every request made through it and returns a configurable response.
    """

    def __init__(self) -> None:
        self.requests: list[SingleJson] = []
        self.response: MagicMock = MagicMock()
        self.response.status_code = 200
        self.response.text = ""
        self.error: Exception | None = None

    def request(self, method: str, url: str, **kwargs: object) -> MagicMock:
        self.requests.append({"method": method, "url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return self.response


class GetFederationCasesStub:
    """Stub replacement for TIPCommon's `get_federation_cases`.

    Records every call and returns a configurable mock response.
    """

    def __init__(self) -> None:
        self.calls: list[SingleJson] = []
        self.response: MagicMock = MagicMock()
        self.response.status_code = 200
        self.response.json.return_value = {"cases": [], "continuationToken": None}

    def __call__(self, **kwargs: object) -> MagicMock:
        self.calls.append(kwargs)
        return self.response


class PatchFederationCasesStub:
    """Stub replacement for TIPCommon's `patch_federation_cases`.

    Records every call and returns a configurable mock response.
    """

    def __init__(self) -> None:
        self.calls: list[SingleJson] = []
        self.response: MagicMock = MagicMock()
        self.response.status_code = 200
        self.response.text = ""

    def __call__(self, **kwargs: object) -> MagicMock:
        self.calls.append(kwargs)
        return self.response
