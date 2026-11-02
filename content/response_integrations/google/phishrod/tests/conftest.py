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

"""
Tests configuration file
"""
import pytest
from _pytest.monkeypatch import MonkeyPatch

from ..core.PhishrodExceptions import PhishrodException
from ..core.PhishrodManager import PhishrodManager


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the test connectivity function to raise phishrod exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise PhishrodException("Connectivity error")

    monkeypatch.setattr(
        PhishrodManager,
        "test_connectivity",
        mock_raise_manager_error,
    )


@pytest.fixture
def mock_get_incidents_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the get incidents function to raise phishrod exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise PhishrodException("Get incidents error")

    monkeypatch.setattr(
        PhishrodManager,
        "get_incidents",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_mark_incident_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the mark incident function to raise phishrod exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise PhishrodException("Mark incident error")

    monkeypatch.setattr(
        PhishrodManager,
        "mark_incident",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_update_incident_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    """
    Mock the update incidents function to raise phishrod exception
    """

    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise PhishrodException("Update incident error")

    monkeypatch.setattr(
        PhishrodManager,
        "update_incident",
        mock_raise_manager_error,
    )

