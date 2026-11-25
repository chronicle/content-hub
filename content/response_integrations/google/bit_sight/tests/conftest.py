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
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import soar_sdk  # noqa: F401

from bit_sight.core.BitSightExceptions import BitSightException
from bit_sight.core.BitSightManager import BitSightManager
from bit_sight.tests.common import CONFIG, TESTS_DIR

if TYPE_CHECKING:
    from collections.abc import Iterator


class MockResponse:
    """Lightweight mock HTTP response for BitSight unit tests."""

    def __init__(self, json_data: dict[str, object], status_code: int) -> None:
        """Initialize mock response payload and HTTP status code."""
        self.json_data = json_data
        self.status_code = status_code

    def json(self) -> dict[str, object]:
        """Return the mocked JSON payload."""
        return self.json_data


def _load_fixture_json(filename: str) -> dict[str, object]:
    """Load a JSON fixture file from the BitSight tests directory."""
    return json.loads((TESTS_DIR / filename).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bitsight_manager() -> Iterator[BitSightManager]:
    """Provide a configured BitSightManager instance for unit tests."""
    yield BitSightManager(
        api_root=str(CONFIG.get("API Root", "")),
        api_key=str(CONFIG.get("API Key", "")),
        verify_ssl=bool(CONFIG.get("Verify SSL", True)),
        siemplify_logger=MagicMock(),
    )


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch BitSightManager.test_connectivity to raise an authentication error."""

    def mock_raise_manager_error(*_args: object, **_kwargs: object) -> None:
        raise BitSightException("An error occurred: 401 Client Error")

    monkeypatch.setattr(BitSightManager, "test_connectivity", mock_raise_manager_error)


@pytest.fixture
def mock_get_company_details_raise_manager_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch BitSightManager.get_company_details to raise a not-found error."""

    def mock_raise_manager_error(*_args: object, **_kwargs: object) -> None:
        raise BitSightException("An error occurred: 404 Client Error")

    monkeypatch.setattr(BitSightManager, "get_company_details", mock_raise_manager_error)


@pytest.fixture
def mock_get_company_vulnerabilities_raise_manager_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch BitSightManager.get_company_vulnerabilities to raise a not-found error."""

    def mock_raise_manager_error(*_args: object, **_kwargs: object) -> None:
        raise BitSightException("An error occurred: 404 Client Error")

    monkeypatch.setattr(BitSightManager, "get_company_vulnerabilities", mock_raise_manager_error)


def mock_get_companies_response(*_args: object, **_kwargs: object) -> MockResponse:
    """Return mocked companies response payload."""
    return MockResponse(_load_fixture_json("companies.json"), 200)


def mock_get_vulnerabilities_response(*_args: object, **_kwargs: object) -> MockResponse:
    """Return mocked vulnerabilities response payload."""
    return MockResponse(_load_fixture_json("vulnerabilities.json"), 200)


@pytest.fixture
def mock_get_companies_response_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch BitSightManager.make_request to return mocked companies payload."""
    monkeypatch.setattr(BitSightManager, "make_request", mock_get_companies_response)

