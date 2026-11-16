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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from azure_active_directory.actions.ListMembersInGroup import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

GROUP_ID = "group-abc"
GROUP_NAME = "Test Group"
_MEMBER_1 = {
    "id": "uid-m1",
    "displayName": "Alice",
    "userPrincipalName": "alice@contoso.com",
    "mail": "alice@contoso.com",
    "jobTitle": "Engineer",
    "mobilePhone": None,
    "businessPhones": [],
    "officeLocation": None,
    "preferredLanguage": None,
    "surname": "Smith",
    "givenName": "Alice",
}
_GROUP_RAW = {
    "id": GROUP_ID,
    "displayName": GROUP_NAME,
    "description": "A test group",
    "createdDateTime": "2024-01-01T00:00:00Z",
    "groupTypes": [],
    "mailNickname": GROUP_NAME,
    "onPremisesSamAccountName": None,
}


class TestListMembersInGroup:
    def test_list_members_success_with_group_id(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing members when group is identified by ID."""
        product.add_group_member(GROUP_ID, _MEMBER_1)
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        action_params["Max Records To Return"] = 50
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully found members" in action_output.output_message
        assert isinstance(json_results.json_results, list)
        assert len(json_results.json_results) == 1
        assert json_results.json_results[0]["id"] == "uid-m1"

    def test_list_members_success_with_group_name(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing members when group is identified by name."""
        product.add_group(GROUP_ID, _GROUP_RAW)
        product.add_group_member(GROUP_ID, _MEMBER_1)
        action_params["Group ID"] = None
        action_params["Group Name"] = GROUP_NAME
        action_params["Max Records To Return"] = 50
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "Successfully found members" in action_output.output_message

    def test_list_members_no_members_found(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test when the group exists but has no members."""
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        action_params["Max Records To Return"] = 50
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No members were found" in action_output.output_message

    def test_list_members_neither_group_id_nor_name(
        self,
        _product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that providing neither Group ID nor Group Name raises FAILED."""
        action_params["Group ID"] = None
        action_params["Group Name"] = None
        action_params["Max Records To Return"] = 50
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert 'Group ID' in action_output.output_message or 'Group Name' in action_output.output_message

    def test_list_members_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_group_member(GROUP_ID, _MEMBER_1)
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        action_params["Max Records To Return"] = 50
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_list_members_invalid_limit(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        _mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a non-positive limit raises FAILED.

        ISSUE FINDER: Max Records To Return validation raises a generic Exception
        that surfaces as FAILED — the message 'Positive number should be provided'
        is correct but the user also sees the action name prefix which makes it
        verbose and inconsistent with the ping/enrich pattern.
        """
        product.add_group_member(GROUP_ID, _MEMBER_1)
        action_params["Group ID"] = GROUP_ID
        action_params["Group Name"] = None
        action_params["Max Records To Return"] = 0
        action_params["Filter Logic"] = None
        action_params["Filter Key"] = "Select One"
        action_params["Filter Value"] = None

        main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert "Positive number" in action_output.output_message
