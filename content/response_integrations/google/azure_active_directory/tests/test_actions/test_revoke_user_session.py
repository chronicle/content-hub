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
from typing import Any
from unittest.mock import MagicMock
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from azure_active_directory.actions.RevokeUserSession import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"
USER_DISPLAY_NAME = "Alex Wilber"
USER_ID = "uid-alex-revoke"


class TestRevokeUserSession:
    def test_revoke_session_success_by_email(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test revoking a session when the entity identifier is an email address."""
        product.add_user(
            USER_EMAIL,
            {
                "userPrincipalName": USER_EMAIL,
                "mail": USER_EMAIL,
                "displayName": USER_DISPLAY_NAME,
                "id": USER_ID,
            },
        )
        product.set_revoke_session_result(USER_ID, {"value": True})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully revoked sessions" in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_revoke_session_success_by_display_name(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test revoking a session when the entity identifier is a display name."""
        product.add_user(
            USER_DISPLAY_NAME,
            {
                "userPrincipalName": USER_EMAIL,
                "mail": USER_EMAIL,
                "displayName": USER_DISPLAY_NAME,
                "id": USER_ID,
            },
        )
        product.set_revoke_session_result(USER_ID, {"value": True})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier=USER_DISPLAY_NAME, entity_type=EntityTypes.USER
            )
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully revoked sessions" in action_output.output_message

    def test_revoke_session_user_not_found(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that a user not found in AAD results in a failure message without crashing.

        ISSUE FINDER: When get_user_id_with_filter raises AzureADNotFoundError the
        action correctly appends to failed_entities, but when ALL entities fail the
        output says "None of the provided users were found" and result_value=False.
        The JSON result still contains {"error": "User not found"} entries which is
        technically a JSON result side-effect even for the failed case.
        """
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="ghost@domain.com", entity_type=EntityTypes.USER
            )
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "None of the provided users were found" in action_output.output_message

    def test_revoke_session_no_entities(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test with no user entities returns False."""
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False

    def test_revoke_session_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user(
            USER_EMAIL,
            {
                "userPrincipalName": USER_EMAIL,
                "mail": USER_EMAIL,
                "displayName": USER_DISPLAY_NAME,
                "id": USER_ID,
            },
        )
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
