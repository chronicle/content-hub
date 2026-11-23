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
from unittest.mock import MagicMock, patch
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from azure_active_directory.actions.ResetUserPassword import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"
NEW_PASSWORD = "N3wS3cur3P@ssw0rd!"


class TestResetUserPassword:
    def test_reset_password_success_via_entity(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test successfully resetting password for an entity."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-5"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Password"] = NEW_PASSWORD
        action_params["Username"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Password was successfully changed" in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_reset_password_success_via_param(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test resetting password using the Username action parameter."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-5"})
        mock_siemplify.target_entities = []
        action_params["Password"] = NEW_PASSWORD
        action_params["Username"] = USER_EMAIL

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Password was successfully changed" in action_output.output_message

    def test_reset_password_no_targets(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test with no targets and no Username param returns False."""
        mock_siemplify.target_entities = []
        action_params["Password"] = NEW_PASSWORD
        action_params["Username"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No user passwords were reset" in action_output.output_message

    def test_reset_password_complexity_error(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that password complexity errors result in a FAILED action."""
        from azure_active_directory.core.exceptions import AzurePasswordComplexityError

        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-5"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Password"] = "weak"
        action_params["Username"] = None

        # Patch on the module that the action script actually imports from
        with patch(
            "azure_active_directory.actions.ResetUserPassword"
            ".AzureADManager.reset_user_password",
            side_effect=AzurePasswordComplexityError("Password complexity error"),
        ):
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert "complexity" in action_output.output_message.lower()

    def test_reset_password_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-5"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Password"] = NEW_PASSWORD
        action_params["Username"] = None

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
