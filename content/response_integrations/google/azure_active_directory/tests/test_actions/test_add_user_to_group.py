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

from azure_active_directory.actions.AddUserToGroup import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"
GROUP_ID = "group-guid-abc123"
USER_ID = "uid-alex"


class TestAddUserToGroup:
    def test_add_user_to_group_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test successfully adding a user to a group."""
        product.add_user(
            USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID}
        )
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Group ID"] = GROUP_ID

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert GROUP_ID in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_add_user_to_group_no_entities(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test with no user entities returns False."""
        mock_siemplify.target_entities = []
        action_params["Group ID"] = GROUP_ID

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No users were added" in action_output.output_message

    def test_add_user_to_group_api_error(
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
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Group ID"] = GROUP_ID

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_add_user_to_group_user_not_found(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that users not found in the directory land in failed_entities.

        ISSUE FINDER: The action silently fails per entity (appending to
        failed_entities) but still reports result_value=False if nothing
        succeeded; the output says 'No users were added' rather than naming
        which users failed — callers can't easily distinguish 'no targets'
        from 'all targets failed'.
        """
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="nonexistent@domain.com", entity_type=EntityTypes.USER
            )
        ]
        action_params["Group ID"] = GROUP_ID

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        # 'No users were added to the group' because the GET for user_id returns 404
        # which raises an exception caught by the per-entity handler
        assert "No users were added" in action_output.output_message
