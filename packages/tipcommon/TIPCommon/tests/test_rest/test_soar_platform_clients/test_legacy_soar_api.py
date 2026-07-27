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

from typing import Any
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from TIPCommon.rest.soar_platform_clients.legacy_soar_api import LegacySoarApi


def test_legacy_save_or_update_job(
    mocker: MockerFixture, mock_chronicle_soar: MagicMock, mock_get_sdk_api_uri: MagicMock
) -> None:
    """Test save_or_update_job makes the correct POST request to legacy SOAR API."""
    client = LegacySoarApi(mock_chronicle_soar)
    job_data = {"id": 1, "parameters": []}
    params: Any = client.params
    params.job_data = job_data

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_chronicle_soar.session.request.return_value = mock_response

    res = client.save_or_update_job()

    assert res == mock_response
    mock_chronicle_soar.session.request.assert_called_once_with(
        "POST",
        "https://mock-soar-api.com/jobs/SaveOrUpdateJobData",
        params=None,
        json=job_data,
    )
