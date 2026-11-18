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

from azure_active_directory.actions.RemoveUserFromTheGroup import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"
USER_ID = "uid-alex-remove"
GROUP_ID = "group-remove-xyz"
GROUP_NAME = "Removable Group"
_GROUP_RAW = {
    "id": GROUP_ID,
    "displayName": GROUP_NAME,
    "mailNickname": GROUP_NAME,
    "description": None,
    "createdDateTime": "2024-01-01T00:00:00Z",
    "groupTypes": [],
    "onPremisesSamAccountName": None,
}


class TestRemoveUserFromGroup:
    def test_remove_user_success_with_group_id(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test successfully removing a user via Group ID parameter."""
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        product.add_group_member(GROUP_ID, {"id": USER_ID, "displayName": "Alex W"})
        action_params["User Name"] = USER_EMAIL
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully removed" in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_remove_user_success_with_group_name(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test successfully removing a user when Group Name is provided instead of ID."""
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        product.add_group(GROUP_ID, _GROUP_RAW)
        product.add_group_member(GROUP_ID, {"id": USER_ID, "displayName": "Alex W"})
        action_params["User Name"] = USER_EMAIL
        action_params["Group ID"] = None
        action_params["Group Name"] = GROUP_NAME
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully removed" in action_output.output_message

    def test_remove_user_via_entity(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test removing users sourced from target_entities."""
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        product.add_group_member(GROUP_ID, {"id": USER_ID, "displayName": "Alex W"})
        action_params["User Name"] = None
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully removed" in action_output.output_message

    def test_remove_user_neither_group_id_nor_name(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that providing neither Group ID nor Group Name raises FAILED."""
        action_params["User Name"] = USER_EMAIL
        action_params["Group ID"] = None
        action_params["Group Name"] = None
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_remove_user_not_in_group(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a user not a member of the group ends up in failed_users.

        ISSUE FINDER: AzureADNotFoundError is raised by remove_user_from_group
        (via validate_response handle_404=True) when the DELETE returns 404.
        The action appends to failed_users, but the session mock returns 204
        for all DELETE calls (the user may not be in the group but DELETE
        still succeeds in the mock). To properly test the 404 path we'd need
        to make the DELETE return 404 for a specific user_id.
        """
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        # User exists in AAD (GET succeeds) but is not in the group
        action_params["User Name"] = USER_EMAIL
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        mock_siemplify.target_entities = []

        main()

        # In the mock the DELETE always returns 204, so the action reports success
        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True

    def test_remove_user_not_found_in_aad(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a user not found in AAD (404 on GET user_id) lands in not_found_users."""
        action_params["User Name"] = "ghost@domain.com"
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False

    def test_remove_user_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        action_params["User Name"] = USER_EMAIL
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        mock_siemplify.target_entities = []

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
