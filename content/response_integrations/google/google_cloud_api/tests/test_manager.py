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

from bs4 import BeautifulSoup

from google_cloud_api.core.GoogleCloudApiManager import ApiManager
from google_cloud_api.tests.core.session import GoogleCloudApiSession


class TestGoogleCloudApiManager:
    """Unit tests for GoogleCloudApi ApiManager."""

    def test_execute_http_request_valid_success(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            gcloud_api_manager: ApiManager,
    ) -> None:
        response = gcloud_api_manager.execute_http_request(
            method="GET",
            url_path="https://example.com/get_test_resource"
        )
        response_json = response.json()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/get_test_resource"
        )
        assert (
            gcloud_api_script_session.request_history[-1].request.url.netloc
            == "example.com"
        )
        assert response_json.get("name") == "test-resource"
        assert response.status_code == 200

    def test_execute_http_request_invalid_failed(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            gcloud_api_manager: ApiManager,
    ) -> None:

        response = gcloud_api_manager.execute_http_request(
            method="POST",
            url_path="https://example.com/post_error"
        )
        response_json = response.json()

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/post_error"
        )
        assert response_json.get("error", {}).get("message") == (
            "Failed to execute request"
        )
        assert response.status_code == 400

    def test_execute_http_request_xml_response(
            self,
            gcloud_api_script_session: GoogleCloudApiSession,
            gcloud_api_manager: ApiManager,
    ) -> None:

        response = gcloud_api_manager.execute_http_request(
            method="GET",
            url_path="https://example.com/get_xml_response"
        )

        assert len(gcloud_api_script_session.request_history) >= 3
        assert (
            gcloud_api_script_session.request_history[-1].request.url.path
            == "/get_xml_response"
        )
        assert BeautifulSoup(response.text, "xml")
        assert response.status_code == 200
