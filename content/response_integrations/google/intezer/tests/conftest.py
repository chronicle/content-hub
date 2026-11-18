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

"""Tests configuration file"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
import soar_sdk  # noqa: F401
from _pytest.monkeypatch import MonkeyPatch
from intezer.core.IntezerManager import (
    IntezerManager,
)
from intezer.core.exceptions import (
    IntezerManagerError,
    IntezerBadRequestError,
)
from intezer.tests import const

@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test connectivity function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Connectivity error")
    monkeypatch.setattr(
        IntezerManager,
        "test_connectivity",
        mock_raise_manager_error,
    )

@pytest.fixture
def intezer_manager(monkeypatch: MonkeyPatch) -> IntezerManager:
    """intezer manager function load config from config.json file.

    Returns:
        Manager
    """
    with open(const.CONFIG_FILE_NAME, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    api_root = config.get("API Root")
    api_key = config.get("API key")
    verify_ssl = bool(config.get("Verify SSL"))

    monkeypatch.setattr(
        IntezerManager,
        "obtain_access_token",
        lambda *_args, **_kwargs: "dummy-access-token",
    )
    manager = IntezerManager(
        api_root=api_root,
        api_key=api_key,
        verify_ssl=verify_ssl
    )
    manager.session = MagicMock()

    return manager

@pytest.fixture
def mock_get_detonate_file_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("IntezerNotFoundError")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_file",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_detonate_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate_hash function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Detonate Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_index_id_from_file_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_index_id_from_file_hash function
        to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Index Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_index_id_from_file_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_unset_index_file_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test unset_index_file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Unset Index File Error")
    monkeypatch.setattr(
        IntezerManager,
        "unset_index_file",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_suspicious_email_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_suspicious_email function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerBadRequestError("Bad Request Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_suspicious_email",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_detonate_url_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_detonate_url function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Detonate URL Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_detonate_url",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_alert_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_alert function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get Alert Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_alert",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_file_report_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_file_report function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get File Report Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_file_report",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_get_url_report_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test get_url_report function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Get URl Report Error")
    monkeypatch.setattr(
        IntezerManager,
        "get_url_report",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_alert_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_alert function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Submit Alert Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_alert",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_submit_hash_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test submit_hash file function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Submit Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "submit_hash",
        mock_raise_manager_error,
    )

@pytest.fixture
def mock_is_analysis_completed_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """Mock the test is_analysis_completed function to raise Intezer exception
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise IntezerManagerError("Hash Error")
    monkeypatch.setattr(
        IntezerManager,
        "is_analysis_completed",
        mock_raise_manager_error,
    )
