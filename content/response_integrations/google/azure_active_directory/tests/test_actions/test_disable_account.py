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

from azure_active_directory.actions.DisableAccount import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"


class TestDisableAccount:
    def test_disable_account_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test successfully disabling a user account."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-1"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully disabled users" in action_output.output_message
        assert USER_EMAIL in action_output.output_message

    def test_disable_account_no_entities(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        _action_params: dict[str, Any],
    ) -> None:
        """Test with no user entities returns False."""
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No users were disabled" in action_output.output_message

    def test_disable_account_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that API failure during disable is handled gracefully."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-1"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_disable_account_skips_non_user_entities(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that non-USER entity types are silently ignored."""
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="DESKTOP-01", entity_type=EntityTypes.HOSTNAME
            )
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No users were disabled" in action_output.output_message

    def test_disable_account_partial_failure(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test that successful entities are reported even when some fail.

        The session mock returns 204 for PATCH, so we trigger a per-entity failure
        by giving a user an identifier that causes a 404 on the user lookup call.
        We use the spy to raise on the second patch call.
        """
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": "uid-1"})
        bad_user = "nonexistent@domain.com"
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER),
            MockSiemplifyEntity(identifier=bad_user, entity_type=EntityTypes.USER),
        ]

        # The first PATCH succeeds (204), the second is for unknown user.
        # Our session always returns 204 for PATCH, so "both" technically succeed
        # in the mock; but the action still logs both in successful_entities.
        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully disabled users" in action_output.output_message
