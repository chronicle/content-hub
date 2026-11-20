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

from unittest.mock import Mock
import pytest
from _pytest.monkeypatch import MonkeyPatch
import requests
from trend_micro_ddan.core.TrendMicroDDANManager import TrendMicroDDANManager
from trend_micro_ddan.core.TrendMicroDDANExceptions import TrendMicroDDANException


@pytest.fixture
def mock_test_connectivity_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred: 401 Client Error")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'test_connectivity',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_register_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'register',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_unregister_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'unregister',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_check_duplicate_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'check_duplicate',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_submit_sample_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'submit_sample',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_report_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'get_report',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_event_logs_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'get_event_logs',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_suspicious_objects_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'get_suspicious_objects',
        mock_raise_manager_error
    )


@pytest.fixture
def mock_get_screenshot_to_raise_manager_error(monkeypatch: MonkeyPatch) -> None:
    def mock_raise_manager_error(*args, **kwargs) -> None:
        raise TrendMicroDDANException("An error occurred")

    monkeypatch.setattr(
        TrendMicroDDANManager,
        'get_screenshot',
        mock_raise_manager_error
    )

@pytest.fixture
def mock_get_request_with_return_none(monkeypatch: MonkeyPatch) -> None:
    def mock_get_request(*args, **kwargs):
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_response.status_code = 200
        mock_response.content = b'abcdefg'

        return mock_response

    monkeypatch.setattr(requests.Session, 'get', mock_get_request)


@pytest.fixture
def mock_post_request_for_manager(monkeypatch: MonkeyPatch) -> None:
    def mock_post_request(*args, **kwargs):
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_response.status_code = 200

        return mock_response

    monkeypatch.setattr(requests.Session, 'post', mock_post_request)