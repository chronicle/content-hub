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

from azure_active_directory.actions.IsUserInGroup import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "AlexW@Contoso.com"
USER_ID = "uid-alex"
GROUP_ID = "group-guid-xyz"


class TestIsUserInGroup:
    def test_user_is_in_group(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test when the user is a member of the group."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID})
        product.add_group_member(GROUP_ID, {"id": USER_ID, "displayName": "Alex W"})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Group ID"] = GROUP_ID

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Following users were found in the group" in action_output.output_message
        assert USER_EMAIL in action_output.output_message
        assert json_results.json_results  # some JSON result was set

    def test_user_not_in_group(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test when the user exists but is NOT a member of the group."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID})
        # Do NOT add user to the group
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Group ID"] = GROUP_ID

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        # User was processed successfully even though not in group
        assert "Successfully processed entities" in action_output.output_message

    def test_no_user_entities(
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
        assert "No user was found in the group" in action_output.output_message

    def test_is_user_in_group_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user(USER_EMAIL, {"userPrincipalName": USER_EMAIL, "id": USER_ID})
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["Group ID"] = GROUP_ID

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
