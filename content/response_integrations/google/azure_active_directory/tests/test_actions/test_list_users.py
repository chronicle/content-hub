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

from azure_active_directory.actions.ListUsers import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

_USER_1 = {
    "userPrincipalName": "alice@contoso.com",
    "displayName": "Alice",
    "id": "uid-alice",
    "mail": "alice@contoso.com",
    "jobTitle": "Engineer",
    "mobilePhone": None,
    "businessPhones": [],
    "officeLocation": None,
}
_USER_2 = {
    "userPrincipalName": "bob@contoso.com",
    "displayName": "Bob",
    "id": "uid-bob",
    "mail": "bob@contoso.com",
    "jobTitle": "Manager",
    "mobilePhone": None,
    "businessPhones": [],
    "officeLocation": None,
}


class TestListUsers:
    def test_list_users_success(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing users returns correct results."""
        product.add_user("alice@contoso.com", _USER_1)
        product.add_user("bob@contoso.com", _USER_2)
        action_params["Filter"] = "All Fields"
        action_params["Order By"] = "ASC"
        action_params["Order By Field"] = "displayName"
        action_params["Advanced Filter Logic"] = "Equal"
        action_params["Advanced Filter Value"] = None
        action_params["Results Limit"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert "List of users fetched successfully" in action_output.output_message
        assert isinstance(json_results.json_results, list)
        assert len(json_results.json_results) >= 1

    def test_list_users_no_results(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test listing users when directory is empty."""
        product.users.clear()
        action_params["Filter"] = "All Fields"
        action_params["Order By"] = "ASC"
        action_params["Order By Field"] = "displayName"
        action_params["Advanced Filter Logic"] = "Equal"
        action_params["Advanced Filter Value"] = None
        action_params["Results Limit"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is False
        assert "No users were returned" in action_output.output_message

    def test_list_users_api_error(
        self,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that a global API failure surfaces as FAILED status."""
        product.add_user("alice@contoso.com", _USER_1)
        action_params["Filter"] = "All Fields"
        action_params["Order By"] = "ASC"
        action_params["Order By Field"] = "displayName"
        action_params["Advanced Filter Logic"] = "Equal"
        action_params["Advanced Filter Value"] = None
        action_params["Results Limit"] = None

        with product.fail_all_requests():
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False

    def test_list_users_with_limit(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that the Results Limit parameter is honoured."""
        product.add_user("alice@contoso.com", _USER_1)
        product.add_user("bob@contoso.com", _USER_2)
        action_params["Filter"] = "All Fields"
        action_params["Order By"] = "ASC"
        action_params["Order By Field"] = "displayName"
        action_params["Advanced Filter Logic"] = "Equal"
        action_params["Advanced Filter Value"] = None
        action_params["Results Limit"] = 1

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert action_output.result_value is True
        assert len(json_results.json_results) == 1

    def test_list_users_wrong_filter_raises_failed(
        self,
        product: AzureADProduct,
        _script_session: AzureADSession,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that using an advanced filter with an unsupported field returns FAILED.

        ISSUE FINDER: The action raises AzureWrongFiltersError when filter_value is
        set but filter_fields is not one of the priority fields. The resulting output
        message says 'Failed to run the action with advanced filtering' which is
        accurate but gives no hint about which field was invalid.
        """
        product.add_user("alice@contoso.com", _USER_1)
        action_params["Filter"] = "displayName"  # not in USERS_LIST_PRIORITY_FILDS
        action_params["Order By"] = "ASC"
        action_params["Order By Field"] = "displayName"
        action_params["Advanced Filter Logic"] = "Equal"
        action_params["Advanced Filter Value"] = "alice"
        action_params["Results Limit"] = None

        main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert "advanced filtering" in action_output.output_message.lower()
