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

"""Tests for the ChangeAccountPassword action in CyberArk PAM integration."""


from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import requests
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from cyber_ark_pam.actions import ChangeAccountPassword
from cyber_ark_pam.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


class TestChangeAccountPassword:
    """Test suite for the ChangeAccountPassword action."""
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "28_11"})
    def test_change_password_success(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test successfully marking an account for password rotation."""
        ChangeAccountPassword.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            "Successfully queued an immediate password change task in CyberArk PAM for the following accounts: 28_11"
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": ["28_11"],
            "failed_accounts": [],
        }

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "25_30"})
    def test_change_password_all_fail(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test the all-failed scenario where all accounts fail to rotate."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        mock_error_response.reason = "Bad Request"
        mock_error_response.json.side_effect = ValueError("No JSON")
        mock_error_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Client Error: Bad Request", response=mock_error_response
        )

        def mock_post_fail(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None

                return mock_logon

            return mock_error_response

        mock_session.post.side_effect = mock_post_fail

        ChangeAccountPassword.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "None of the provided accounts were queued for a password change task. Please check JSON Result for more information."
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [],
            "failed_accounts": [
                {"account_id": "25_30", "error": "Bad Request"}
            ],
        }

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "28_11, 25_30"})
    def test_change_password_mixed(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test mixed success and failure scenario."""
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.text = ""
        success_response.raise_for_status.return_value = None

        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        mock_error_response.reason = "Bad Request"
        mock_error_response.json.side_effect = ValueError("No JSON")
        mock_error_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Client Error: Bad Request", response=mock_error_response
        )

        def mock_post_mixed(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_status.return_value = None

                return mock_logon
            if "28_11/Change" in url:
                return success_response
            if "25_30/Change" in url:
                return mock_error_response

            return MagicMock(status_code=404)

        mock_session.post.side_effect = mock_post_mixed

        ChangeAccountPassword.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "Successfully queued an immediate password change task in CyberArk PAM for the following accounts: 28_11"
            in action_output.results.output_message
        )
        assert (
            "Action wasn't able to queue an immediate password change task in CyberArk PAM for the following accounts: 25_30. Please check JSON Result for more information."
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": ["28_11"],
            "failed_accounts": [
                {"account_id": "25_30", "error": "Bad Request"}
            ],
        }

    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters={"Account ID": "36_4"})
    def test_change_password_account_not_managed(
        self,
        action_output: MockActionOutput,
        mock_session: MagicMock,
    ) -> None:
        """Test the scenario where the account is not managed by CPM (ErrorCode: CAWS00001E)."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        mock_error_response.json.return_value = {
            "ErrorCode": "CAWS00001E",
            "ErrorMessage": "The account is not managed by the CPM",
        }
        mock_error_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Client Error: Bad Request", response=mock_error_response
        )

        def mock_post_fail(url: str, *args: Any, **kwargs: Any) -> MagicMock:
            if "/Auth/CyberArk/Logon" in url:
                mock_logon = MagicMock()
                mock_logon.status_code = 200
                mock_logon.text = '"mock-token"'
                mock_logon.raise_for_value = None
                mock_logon.raise_for_status.return_value = None

                return mock_logon

            return mock_error_response

        mock_session.post.side_effect = mock_post_fail

        ChangeAccountPassword.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert (
            "None of the provided accounts were queued for a password change task. Please check JSON Result for more information."
            in action_output.results.output_message
        )
        assert action_output.results.json_output.json_result == {
            "successful_accounts": [],
            "failed_accounts": [
                {"account_id": "36_4", "error": "The account is not managed by the CPM"}
            ],
        }
