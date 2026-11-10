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
import json
from typing import Any
from unittest.mock import MagicMock, patch
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from azure_active_directory.actions.GetManagerContactDetails import (
    main,
)
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
    MOCK_RESPONSES,
)
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession


MANAGER_FULL_PROFILE_WITH_SPONSORS = MOCK_RESPONSES[
    "manager_full_profile_with_sponsors"
]


class TestGetManagerContactDetails:
    def test_success_with_fields(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        user_email = "user@company.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        fields_to_return = "displayName,mobilePhone,mail,department"
        action_params["Fields To Return"] = fields_to_return
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully processed entities" in action_output.output_message
        assert user_email in action_output.output_message

        expected_manager_data = MOCK_RESPONSES["manager_custom_fields_response"]
        expected_result_json = {
            "Entity": user_email,
            "EntityResult": expected_manager_data,
        }
        assert len(json_results.json_results) == 1
        assert json_results.json_results[0] == expected_result_json

        call_args, call_kwargs = script_session.get.call_args
        assert "/manager" in call_args[0]
        assert "/microsoft.graph.user" not in call_args[0]
        assert call_kwargs["params"]["$select"] == fields_to_return
        assert "$expand" not in call_kwargs["params"]

    def test_success_default_fields(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        user_email = "user2@company.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        action_params["Fields To Return"] = None
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully processed entities" in action_output.output_message

        expected_manager_data = MOCK_RESPONSES["manager_default_response"]
        expected_result_json = {
            "Entity": user_email,
            "EntityResult": expected_manager_data,
        }
        assert len(json_results.json_results) == 1
        assert json_results.json_results[0] == expected_result_json

        call_args, call_kwargs = script_session.get.call_args
        assert "/manager" in call_args[0]
        assert "/microsoft.graph.user" not in call_args[0]
        assert call_kwargs["params"]["$select"] == "displayName,mobilePhone,mail"
        assert "$expand" not in call_kwargs["params"]

    def test_manager_not_found(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        user_email = "orphan@company.com"
        assert product.get_manager(user_email) is None

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]
        action_params["Fields To Return"] = None

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert (
            "There are no entities containing manager contact details"
            in action_output.output_message
        )
        assert action_output.result_value is False
        assert not json_results.json_results

        call_args, call_kwargs = script_session.get.call_args
        assert "/manager" in call_args[0]
        assert "/microsoft.graph.user" not in call_args[0]
        assert call_kwargs["params"]["$select"] == "displayName,mobilePhone,mail"
        assert "$expand" not in call_kwargs["params"]

    def test_sponsors_field(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        user_email = "user_sponsors@company.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        fields_to_return = "displayName,sponsors"
        action_params["Fields To Return"] = fields_to_return
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert user_email in action_output.output_message

        expected_manager_data = MOCK_RESPONSES["manager_sponsors_response"]
        expected_result_json = {
            "Entity": user_email,
            "EntityResult": expected_manager_data,
        }
        assert len(json_results.json_results) == 1
        assert json_results.json_results[0] == expected_result_json

        call_args, call_kwargs = script_session.get.call_args
        assert "/manager/microsoft.graph.user" in call_args[0]
        assert call_kwargs["params"]["$select"] == "displayName"
        assert call_kwargs["params"]["$expand"] == "sponsors"

    def test_success_all_fields(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        user_email = "user_all@company.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        all_fields_list = [
            "accountEnabled", "ageGroup", "assignedLicenses", "businessPhones",
            "city", "companyName", "consentProvidedForMinor", "country",
            "createdDateTime", "creationType", "department", "displayName",
            "mail", "employeeId", "employeeHireDate", "employeeOrgData",
            "employeeType", "onPremisesExtensionAttributes",
            "externalUserStateChangeDateTime", "faxNumber", "givenName",
            "imAddresses", "identities", "externalUserState", "jobTitle",
            "surname", "lastPasswordChangeDateTime", "legalAgeGroupClassification",
            "mailNickname", "mobilePhone", "id", "officeLocation",
            "onPremisesSamAccountName", "onPremisesDistinguishedName",
            "onPremisesDomainName", "onPremisesImmutableId",
            "onPremisesLastSyncDateTime", "onPremisesProvisioningErrors",
            "onPremisesSecurityIdentifier", "onPremisesSyncEnabled",
            "onPremisesUserPrincipalName", "otherMails", "passwordPolicies",
            "passwordProfile", "preferredDataLocation", "preferredLanguage",
            "proxyAddresses", "signInSessionsValidFromDateTime", "sponsors",
            "state", "streetAddress", "usageLocation", "userPrincipalName",
            "userType", "postalCode", "authorizationInfo", "deletedDateTime",
            "showInAddressList", "isResourceAccount",
            "refreshTokensValidFromDateTime"
        ]
        all_fields = ",".join(all_fields_list)

        action_params["Fields To Return"] = all_fields
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert user_email in action_output.output_message

        expected_manager_data = MOCK_RESPONSES["manager_full_profile_with_sponsors"]
        expected_result_json = {
            "Entity": user_email,
            "EntityResult": expected_manager_data,
        }

        assert len(json_results.json_results) == 1
        assert json_results.json_results[0] == expected_result_json

        call_args, _call_kwargs = script_session.get.call_args
        assert "/manager/microsoft.graph.user" in call_args[0]

    def test_multiple_entities_with_sponsors(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        """
        Regression test: Verify that requesting sponsors
        for multiple entities works correctly.
        Previously, the manager modified the input list in-place,
        causing subsequent calls to lose the 'sponsors' field
        and fail to use the correct URL.
        """
        user1_email = "user1@company.com"
        user2_email = "user2@company.com"

        product.add_manager(user1_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)
        product.add_manager(user2_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user1_email, entity_type=EntityTypes.USER),
            MockSiemplifyEntity(identifier=user2_email, entity_type=EntityTypes.USER)
        ]

        fields_to_return = "displayName,sponsors"
        action_params["Fields To Return"] = fields_to_return
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert user1_email in action_output.output_message
        assert user2_email in action_output.output_message

        assert len(json_results.json_results) == 2

        expected_data = MOCK_RESPONSES["manager_sponsors_response"]

        result1 = next(
            r for r in json_results.json_results if r["Entity"] == user1_email
        )
        assert result1["EntityResult"] == expected_data

        result2 = next(
            r for r in json_results.json_results if r["Entity"] == user2_email
        )
        assert result2["EntityResult"] == expected_data

        assert script_session.get.call_count == 2
        calls = script_session.get.call_args_list

        for call in calls:
            args, kwargs = call
            assert "/manager/microsoft.graph.user" in args[0]
            assert kwargs["params"]["$expand"] == "sponsors"
            assert kwargs["params"]["$select"] == "displayName"

    def test_success_with_mfa_details(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        fields_to_return = "displayName,mobilePhone,mail,department,userPrincipalName"
        include_mfa_details = True
        action_params["Fields To Return"] = fields_to_return
        action_params["Include MFA Details"] = include_mfa_details
        action_params["Include Last Sign In Details"] = False
        user_email = "AlexW@Contoso.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)
        manager_upn = MANAGER_FULL_PROFILE_WITH_SPONSORS["userPrincipalName"]
        product.add_user_registration_details(
            user_principal_name=manager_upn,
            details={"isMfaRegistered": True},
        )

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]
        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully processed entities" in action_output.output_message
        assert user_email in action_output.output_message
        assert action_output.result_value is True

        results = json_results.json_results

        entity_result = None
        for item in results:
            if item.get("Entity") == user_email:
                entity_result = item.get("EntityResult")
                break

        assert "mfa_details" in entity_result
        assert entity_result["mfa_details"]["isMfaRegistered"] is True
        assert script_session.get.call_count == 3

    def test_success_mfa_no_fields(
        self,
        script_session: AzureADSession,
        product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ):
        """
        Verify that when MFA details are requested without specific fields,
        the default fields are returned, userPrincipalName is used for the query
        but not included in the final result.
        """
        user_email = "mfa_user@company.com"
        product.add_manager(user_email, MANAGER_FULL_PROFILE_WITH_SPONSORS)
        manager_upn = MANAGER_FULL_PROFILE_WITH_SPONSORS["userPrincipalName"]
        product.add_user_registration_details(
            user_principal_name=manager_upn,
            details={"isMfaRegistered": True},
        )

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        action_params["Fields To Return"] = None
        action_params["Include MFA Details"] = True
        action_params["Include Last Sign In Details"] = False

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully processed entities" in action_output.output_message
        assert user_email in action_output.output_message
        assert action_output.result_value is True

        call_args_1, call_kwargs_1 = script_session.get.call_args_list[0]
        select_params_1 = call_kwargs_1["params"]["$select"].split(",")

        assert "/manager" in call_args_1[0]
        assert "displayName" in select_params_1
        assert "userPrincipalName" not in select_params_1

        call_args_2, call_kwargs_2 = script_session.get.call_args_list[1]
        select_params_2 = call_kwargs_2["params"]["$select"].split(",")

        assert "/manager" in call_args_2[0]
        assert select_params_2 == ["userPrincipalName"]

        entity_result = json_results.json_results[0]["EntityResult"]

        assert "mfa_details" in entity_result
        assert entity_result["mfa_details"]["isMfaRegistered"] is True

        assert "userPrincipalName" not in entity_result
        assert "displayName" in entity_result

    def test_get_manager_contact_details_success_with_sign_in_details(
        self,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test GetManagerContactDetails success with sign-in details."""
        action_params["Include MFA Details"] = False
        action_params["Include Last Sign In Details"] = True
        user_email = "AlexW@Contoso.com"
        manager_id = "manager-id-456"

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type=EntityTypes.USER)
        ]

        mock_session_instance = MagicMock()
        mock_session_instance.headers = {}

        def mock_response(json_data, status_code=200):
            response = MagicMock()
            response.status_code = status_code
            response.json.return_value = json_data
            response.content = json.dumps(json_data).encode("utf-8")
            response.raise_for_status.return_value = None
            return response

        mock_session_instance.get.side_effect = [
            mock_response(
                {
                    "id": manager_id,
                    "displayName": "Manager Boss",
                    "mail": "boss@contoso.com",
                    "jobTitle": "Head of Projects",
                }
            ),
            mock_response(
                {"signInActivity": {"lastSignInDateTime": "2024-02-02T10:00:00Z"}}
            ),
        ]

        mock_session_instance.post.return_value = mock_response(
            {"access_token": "mock_token"}
        )

        with patch("requests.Session", return_value=mock_session_instance), patch(
            (
                "azure_active_directory.core.AzureADManager"
                ".requests.Session"
            ),
            return_value=mock_session_instance,
        ):
            main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully processed entities" in action_output.output_message

        results = json_results.json_results
        entity_result = next(
            (
                item.get("EntityResult")
                for item in results
                if item.get("Entity") == user_email
            ),
            None,
        )

        assert entity_result is not None
        assert entity_result["displayName"] == "Manager Boss"
        assert (
            entity_result["sign_in_details"]["lastSignInDateTime"]
            == "2024-02-02T10:00:00Z"
        )
