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
import site
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

# Make `sap_erp` importable as a package and expose soar_sdk's flat modules.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
for site_dir in site.getsitepackages():
    soar_sdk_path = Path(site_dir) / "soar_sdk"
    if soar_sdk_path.exists():
        sys.path.insert(0, str(soar_sdk_path))

from sap_erp.core.sap_erp_manager import SapErpManager  # ruff: ignore[module-import-not-at-top-of-file]

ResponseFactory = Callable[..., requests.Response]


@pytest.fixture
def mock_soar_action() -> Iterator[MagicMock]:
    """Replace SiemplifyAction, which reads sys.argv and stdin on init.

    Yields:
        The mock that every Action built during the test receives.

    """
    soar_action = MagicMock()
    with patch(
        "TIPCommon.base.action.base_action.create_soar_action",
        return_value=soar_action,
    ):
        yield soar_action


def build_response(
    status_code: int = 200,
    json_body: Any = None,  # ruff: ignore[any-type]
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


@pytest.fixture
def manager() -> MagicMock:
    """Mocked SapErpManager that keeps the real static error extractor.

    Returns:
        A spec'd SapErpManager mock.

    """
    mock_manager = MagicMock(spec=SapErpManager)
    mock_manager.extract_error_detail.side_effect = SapErpManager.extract_error_detail
    return mock_manager
