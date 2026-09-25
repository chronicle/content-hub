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
from unittest.mock import MagicMock

import pytest
import requests
from core.constants import FORENSIC_DATA_TYPES, GET_FORENSIC_DATA_QUERY
from core.IllusiveNetworksManager import IllusiveNetworksManager


def test_get_forensic_data_query_constant() -> None:
    """Verify GET_FORENSIC_DATA_QUERY formats to the expected /api/v1/forensics endpoint."""
    api_root: str = "https://mock.illusive.com"
    event_id: str = "event_123"
    data_type: str = FORENSIC_DATA_TYPES["include_sys_info"]

    formatted_url: str = GET_FORENSIC_DATA_QUERY.format(api_root, event_id, data_type)
    assert (
        formatted_url
        == "https://mock.illusive.com/api/v1/forensics?event_id=event_123&type=HOST_INFO"
    )
    assert "GET_INCIDENT_ID_QUERY" not in formatted_url


def test_get_forensic_data_calls_correct_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify manager.get_forensic_data requests the correct forensic URL via session.request."""
    manager: IllusiveNetworksManager = IllusiveNetworksManager(
        api_root="https://mock.illusive.com",
        api_key="mock_key",
        verify_ssl=False,
    )

    mock_response: MagicMock = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "value": json.dumps(
            {
                "osName": "Windows 10",
                "machineType": "Workstation",
                "host": "test.local",
                "loggedInUser": "admin",
                "userProfiles": ["admin"],
                "operatingSystemType": "Windows",
            }
        )
    }

    mock_request: MagicMock = MagicMock(return_value=mock_response)
    monkeypatch.setattr(manager.session, "request", mock_request)

    result = manager.get_forensic_data(
        event_id="event_123",
        include_sys_info=True,
        include_prefetch_files_info=False,
        include_add_remove=False,
        include_startup_info=False,
        include_running_info=False,
        include_user_assist_info=False,
        include_powershell_info=False,
    )

    assert "host_info" in result
    mock_request.assert_called_once_with(
        "GET",
        "https://mock.illusive.com/api/v1/forensics?event_id=event_123&type=HOST_INFO",
        allow_redirects=True,
    )
