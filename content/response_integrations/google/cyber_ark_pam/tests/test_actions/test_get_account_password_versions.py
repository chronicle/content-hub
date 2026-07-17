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

"""Tests for the GetAccountPasswordVersions action in CyberArk PAM integration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from cyber_ark_pam.actions import get_account_password_versions
from cyber_ark_pam.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


class TestGetAccountPasswordVersions:
    """Test suite for the GetAccountPasswordVersions action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "28_11"}
    )
    def test_get_password_versions_success(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test successfully retrieving secret versions for an account."""
        versions_response = MagicMock()
        versions_response.status_code = 200
        versions_response.json.return_value = {"value": [1, 2, 3]}
        versions_response.raise_for_status.return_value = None

        def mock_http_calls(url: str, *args: object, **kwargs: object) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None
                return mock_logon
            if "28_11/Secret/Versions" in url:
                return versions_response
            return MagicMock(status_code=404)

        mock_session.post.side_effect = mock_http_calls
        mock_session.get.side_effect = mock_http_calls

        get_account_password_versions.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            "Successfully retrieved secret versions in CyberArk PAM for the following accounts: 28_11"
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [{"account_id": "28_11", "versions": [1, 2, 3]}],
            "failed_accounts": [],
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "25_30"}
    )
    def test_get_password_versions_all_fail(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test the all-failed scenario where all accounts fail to retrieve versions."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error_response.reason = "Account not found"
        mock_error_response.json.side_effect = ValueError("No JSON")
        mock_error_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Client Error: Account not found", response=mock_error_response
        )

        def mock_http_calls(url: str, *args: object, **kwargs: object) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None
                return mock_logon
            return mock_error_response

        mock_session.post.side_effect = mock_http_calls
        mock_session.get.side_effect = mock_http_calls

        get_account_password_versions.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "None of the provided accounts were retrieved for secret versions. "
            "Please check JSON Result for more information."
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [],
            "failed_accounts": [{"account_id": "25_30", "error": "Account not found"}],
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Account ID": "28_11, 25_30"},
    )
    def test_get_password_versions_mixed(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test mixed success and failure scenario."""
        versions_response = MagicMock()
        versions_response.status_code = 200
        versions_response.json.return_value = {"value": [1, 2]}
        versions_response.raise_for_status.return_value = None

        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error_response.reason = "Account not found"
        mock_error_response.json.side_effect = ValueError("No JSON")
        mock_error_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Client Error: Account not found", response=mock_error_response
        )

        def mock_http_calls(url: str, *args: object, **kwargs: object) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None
                return mock_logon
            if "28_11/Secret/Versions" in url:
                return versions_response
            if "25_30/Secret/Versions" in url:
                return mock_error_response

            return MagicMock(status_code=404)

        mock_session.post.side_effect = mock_http_calls
        mock_session.get.side_effect = mock_http_calls

        get_account_password_versions.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "Successfully retrieved secret versions in CyberArk PAM for the following accounts: 28_11"
            in action_output.results.output_message
        )
        assert (
            "Action wasn't able to retrieve secret versions in CyberArk PAM for the following "
            "accounts: 25_30. Please check JSON Result for more information."
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [{"account_id": "28_11", "versions": [1, 2]}],
            "failed_accounts": [{"account_id": "25_30", "error": "Account not found"}],
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "28_14"}
    )
    def test_get_password_versions_success_with_versions_dict(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test successfully retrieving secret versions for an account where response has nested 'Versions' key."""
        versions_response = MagicMock()
        versions_response.status_code = 200
        versions_response.json.return_value = {
            "Versions": [
                {
                    "versionID": 34,
                    "modifiedBy": "Administrator",
                    "modificationDate": 1784090383,
                    "isTemporary": False,
                },
                {
                    "versionID": 23,
                    "modifiedBy": "Administrator",
                    "modificationDate": 1781785304,
                    "isTemporary": False,
                },
            ],
            "Total": 2,
        }
        versions_response.raise_for_status.return_value = None

        def mock_http_calls(url: str, *args: object, **kwargs: object) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None
                return mock_logon
            if "28_14/Secret/Versions" in url:
                return versions_response
            return MagicMock(status_code=404)

        mock_session.post.side_effect = mock_http_calls
        mock_session.get.side_effect = mock_http_calls

        get_account_password_versions.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [
                {
                    "account_id": "28_14",
                    "versions": [
                        {
                            "versionID": 34,
                            "modifiedBy": "Administrator",
                            "modificationDate": 1784090383,
                            "isTemporary": False,
                        },
                        {
                            "versionID": 23,
                            "modifiedBy": "Administrator",
                            "modificationDate": 1781785304,
                            "isTemporary": False,
                        },
                    ],
                }
            ],
            "failed_accounts": [],
        }
