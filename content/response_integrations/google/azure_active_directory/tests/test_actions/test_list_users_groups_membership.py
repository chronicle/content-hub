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

from azure_active_directory.actions.ListUsersGroupsMembership import (
    main,
)
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

USER_EMAIL = "alice@contoso.com"
GROUP_ID_1 = "group-id-111"
GROUP_ID_2 = "group-id-222"
_GROUP_1 = {
    "id": GROUP_ID_1,
    "displayName": "Security Team",
    "description": "Security group",
    "createdDateTime": "2024-01-01T00:00:00Z",
    "groupTypes": [],
    "securityEnabled": True,
    "mailEnabled": False,
    "mailNickname": "secteam",
    "onPremisesSamAccountName": None,
}
_GROUP_2 = {
    "id": GROUP_ID_2,
    "displayName": "Engineering",
    "description": "Engineering group",
    "createdDateTime": "2024-01-02T00:00:00Z",
    "groupTypes": ["Unified"],
    "securityEnabled": False,
    "mailEnabled": True,
    "mailNickname": "eng",
    "onPremisesSamAccountName": None,
}


class TestListUsersGroupsMembership:
    def test_list_groups_for_entity_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing group memberships for a USER entity."""
        product.add_group(GROUP_ID_1, _GROUP_1)
        product.add_group(GROUP_ID_2, _GROUP_2)
        product.add_user_group_membership(USER_EMAIL, [GROUP_ID_1, GROUP_ID_2])
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["User Name"] = None
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = False
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 50

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully found groups" in action_output.output_message
        assert USER_EMAIL in action_output.output_message
        assert json_results.json_results  # JSON result set

    def test_list_groups_via_username_param(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing groups when username is provided as action parameter."""
        product.add_group(GROUP_ID_1, _GROUP_1)
        product.add_user_group_membership(USER_EMAIL, [GROUP_ID_1])
        mock_siemplify.target_entities = []
        action_params["User Name"] = USER_EMAIL
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = False
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 50

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert USER_EMAIL in action_output.output_message

    def test_list_groups_no_groups_found(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test when user has no group memberships."""
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["User Name"] = None
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = False
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 50

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No groups were found" in action_output.output_message

    def test_list_groups_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_group(GROUP_ID_1, _GROUP_1)
        product.add_user_group_membership(USER_EMAIL, [GROUP_ID_1])
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["User Name"] = None
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = False
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 50

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_list_groups_invalid_limit(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a non-positive limit raises FAILED."""
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["User Name"] = None
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = False
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 0

        main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert "Positive number" in action_output.output_message

    def test_list_groups_detailed_information(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that detailed group information includes raw group data."""
        product.add_group(GROUP_ID_1, _GROUP_1)
        product.add_user_group_membership(USER_EMAIL, [GROUP_ID_1])
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=USER_EMAIL, entity_type=EntityTypes.USER)
        ]
        action_params["User Name"] = None
        action_params["Return Only Security Enabled Groups"] = False
        action_params["Return Detailed Groups Information"] = True
        action_params["Filter Key"] = "Select One"
        action_params["Filter Logic"] = None
        action_params["Filter Value"] = None
        action_params["Max Records To Return"] = 50

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        results = json_results.json_results
        # The dict-to-json-result-dict wraps in {entity: [list_of_groups]}
        assert results
