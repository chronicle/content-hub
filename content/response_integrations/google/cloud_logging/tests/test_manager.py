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
import pathlib

import pytest

from cloud_logging.core.CloudLoggingApiManager import (
    CloudLoggingApiManager,
)
from cloud_logging.core.exceptions import (
    CloudLoggingManagerError,
)
from cloud_logging.tests.core.session import GoogleCloudApiSession


TEST_INPUT_QUERY_PARAMS = {
    "query": 'insertId="8b70da06-b1b1-0000-94ba-000000000000"',
    "project_id": "test_project_id",
    "organization_id": None,
    "time_frame": "Last 6 Hours",
    "start_time": None,
    "end_time": None,
    "max_results": 50,
}


class TestGoogleCloudLoggingManager:
    """Unit tests for GoogleCloudApi ApiManager."""

    def test_execute_query_organization_in_integration_params(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        gcloud_api_manager: CloudLoggingApiManager,
    ) -> None:
        logs, _ = gcloud_api_manager.execute_query(**TEST_INPUT_QUERY_PARAMS)

        assert len(logs) == 1

        assert logs[0]["insertId"] == "8b70da06-b1b1-0000-94ba-000000000000"
        assert len(gcloud_api_script_session.request_history) >= 1
        gcloud_api_script_session.request_history.assert_data(
            {
                "resourceNames": ["projects/test_project_id"],
                "pageSize": 50,
            }
        )
        gcloud_api_script_session.request_history.assert_url_path(
            "/v2/entries:list", "logging.googleapis.com"
        )

    def test_execute_query_organization_in_action_params(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        gcloud_api_manager: CloudLoggingApiManager,
    ) -> None:
        test_params = TEST_INPUT_QUERY_PARAMS.copy()
        test_params["organization_id"] = "mock_organization"
        logs, _ = gcloud_api_manager.execute_query(**test_params)

        assert len(logs) == 1

        assert len(gcloud_api_script_session.request_history) >= 1
        gcloud_api_script_session.request_history.assert_data(
            {
                "resourceNames": ["organizations/mock_organization"],
                "pageSize": 50,
            }
        )
        gcloud_api_script_session.request_history.assert_url_path(
            "/v2/entries:list", "logging.googleapis.com"
        )

    def test_execute_query_organization_not_defined(
        self,
        gcloud_api_script_session: GoogleCloudApiSession,
        gcloud_api_manager: CloudLoggingApiManager,
    ) -> None:

        gcloud_api_manager.organization_id = None
        logs, _ = gcloud_api_manager.execute_query(**TEST_INPUT_QUERY_PARAMS)

        assert len(logs) == 1

        assert len(gcloud_api_script_session.request_history) >= 1
        gcloud_api_script_session.request_history.assert_data(
            {
                "resourceNames": ["projects/test_project_id"],
                "pageSize": 50,
            }
        )
        gcloud_api_script_session.request_history.assert_url_path(
            "/v2/entries:list", "logging.googleapis.com"
        )

    def test_test_conectivity_no_project_and_organization(
        self,
        gcloud_api_manager: CloudLoggingApiManager,
    ) -> None:

        gcloud_api_manager.organization_id = None
        gcloud_api_manager.project_id = None
        with pytest.raises(Exception) as err:
            _ = gcloud_api_manager.test_connectivity()

            assert err.value == "Project id or organization id must be specified"
            assert isinstance(err.value, CloudLoggingManagerError)
