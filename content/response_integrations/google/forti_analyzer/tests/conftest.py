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

import pytest
import soar_sdk  # noqa: F401
from _pytest.monkeypatch import MonkeyPatch

from forti_analyzer.core.FortiAnalyzerExceptions import FortiAnalyzerException
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 401 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'test_connectivity',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_device_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'get_device',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_find_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'find_alert',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_mark_as_read_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'mark_as_read',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_assign_user_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'assign_user',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_acknowledge_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred: 404 Client Error")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'acknowledge_alert',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_add_comment_to_alert_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise FortiAnalyzerException("An error occurred")

    monkeypatch.setattr(
        FortiAnalyzerManager,
        'add_comment_to_alert',
        mock_raise_manager_error
    )
