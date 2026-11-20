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
from collections.abc import Callable
from typing import Any

import pytest
import requests

pytest_plugins = ("integration_testing.conftest",)

ResponseFactory = Callable[..., requests.Response]


def build_response(
    status_code: int = 200,
    json_body: dict[str, Any] | list[Any] | None = None,
    text: str | None = None,
) -> requests.Response:
    """Build a real requests.Response so .ok/.json()/.text behave naturally.

    Returns:
        A response with the given status and body.

    """
    response = requests.Response()
    response.status_code = status_code
    if json_body is not None:
        response._content = json.dumps(json_body).encode("utf-8")
    else:
        response._content = (text or "").encode("utf-8")
    response.encoding = "utf-8"
    return response


@pytest.fixture
def make_response() -> ResponseFactory:
    """Provide the response builder to tests.

    Returns:
        The build_response function.

    """
    return build_response
