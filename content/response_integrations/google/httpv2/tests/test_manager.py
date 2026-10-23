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
import os

from ..core import HTTPV2Manager


# Constants
STATUS_CODES = {
    "SUCCESS": {"status": 200},
    "BAD_REQUEST": {"status": 400},
}

EXECUTE_REQUEST_METHOD = "GET"
EXECUTE_REQUEST_URL_PATH = "https://mock_url_path.com"

with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)


def mock_request(session, request_string, response_code) -> None:
    session.request.return_value = (
        response_code,
        json.dumps(MOCK_DATA.get(request_string)),
    )


class TestHTTPV2Manager:
    """Unit tests for HTTPV2Manager's functions"""

    def test_test_connectivity_valid_success(
        self,
        mocker,
        api_manager: HTTPV2Manager.ApiManager,
    ) -> None:
        mock_data = {}
        mock_get = mocker.Mock()
        mock_get.json.return_value = mock_data
        mocker.patch("requests.Session.get", return_value=mock_get)
        result = api_manager.test_connectivity()

        assert result is None

    def test_execute_http_request_valid_success(
        self,
        api_manager: HTTPV2Manager.ApiManager,
    ) -> None:
        mock_request(
            session=api_manager.session,
            request_string="execute_http_request",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        response_code, response_content = api_manager.execute_http_request(
            method=EXECUTE_REQUEST_METHOD,
            url_path=EXECUTE_REQUEST_URL_PATH
        )

        response_json = json.loads(response_content)

        assert response_json.get("name") == "asd"
        assert response_code == STATUS_CODES.get("SUCCESS")

    def test_execute_http_request_invalid_failed(
        self,
        api_manager: HTTPV2Manager.ApiManager,
    ) -> None:
        mock_request(
            session=api_manager.session,
            request_string="execute_http_request_failed",
            response_code=STATUS_CODES.get("BAD_REQUEST"),
        )

        response_code, response_content = api_manager.execute_http_request(
            method=EXECUTE_REQUEST_METHOD,
            url_path=EXECUTE_REQUEST_URL_PATH
        )

        response_json = json.loads(response_content)

        assert response_json.get("error", {}).get("message") == (
            "Failed to execute request"
        )
        assert response_code == STATUS_CODES.get("BAD_REQUEST")

    def test_execute_http_request_xml_response(
        self,
        api_manager: HTTPV2Manager.ApiManager,
    ) -> None:
        mock_request(
            session=api_manager.session,
            request_string="execute_http_request_xml",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        response_code, response_content = api_manager.execute_http_request(
            method=EXECUTE_REQUEST_METHOD,
            url_path=EXECUTE_REQUEST_URL_PATH
        )

        assert "<?xml" in response_content
        assert response_code == STATUS_CODES.get("SUCCESS")
