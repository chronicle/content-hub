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

from azure_active_directory.actions.ForcePasswordUpdate import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"


class TestForcePasswordUpdate:
    def test_force_password_update_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test successfully forcing a password update for a user."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-3"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "password update was forced" in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_force_password_update_no_entities(
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
        assert "No user's passwords were forced to update" in action_output.output_message

    def test_force_password_update_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-3"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_force_password_update_multiple_users(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test forcing password update for multiple users at once."""
        user2 = "bob@contoso.com"
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-3"})
        product.add_user(user2, {"userPrincipalName": user2, "id": "uid-4"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER),
            MockSiemplifyEntity(identifier=user2, entity_type=EntityTypes.USER),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert USER_EMAIL in action_output.output_message
        assert user2 in action_output.output_message
