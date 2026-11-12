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
from unittest.mock import MagicMock, patch

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.types import SingleJson

from azure_active_directory.actions.EnrichUser import main
from azure_active_directory.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from azure_active_directory.tests.core.product import AzureADProduct


class TestEnrichUser:
    def test_enrich_user_with_mfa_success(
        self,
        azure_ad_product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: SingleJson,
    ) -> None:
        """Test entity enrichment success path with MFA details."""
        action_params["Include MFA Details"] = True
        action_params["Include Last Sign In Details"] = False
        user_email = "AlexW@Contoso.com"

        azure_ad_product.add_user_registration_details(
            user_principal_name=user_email,
            details={"isMfaRegistered": True},
        )

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type="USERUNIQNAME")
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched entities" in action_output.output_message
        assert action_output.result_value is True

        results = json_results.json_results

        entity_result = None
        for item in results:
            if item.get("Entity") == user_email:
                entity_result = item.get("EntityResult")
                break

        assert entity_result is not None, f"Entity {user_email} not found in results"
        assert "mfa_details" in entity_result
        assert entity_result["mfa_details"]["isMfaRegistered"] is True

        entity = mock_siemplify.target_entities[0]
        assert entity.is_enriched is True
        assert "AAD_mfa_details_isMfaRegistered" in entity.additional_properties
        assert entity.additional_properties["AAD_mfa_details_isMfaRegistered"] == "True"

    def test_enrich_user_with_mfa_false(
        self,
        azure_ad_product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: SingleJson,
    ) -> None:
        """
        Test entity enrichment success path with MFA details
        when MFA is not registered.
        """
        action_params["Include MFA Details"] = True
        action_params["Include Last Sign In Details"] = False
        user_email = "AlexW@Contoso.com"

        azure_ad_product.add_user_registration_details(
            user_principal_name=user_email,
            details={"isMfaRegistered": False},
        )

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type="USERUNIQNAME")
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched entities" in action_output.output_message
        assert action_output.result_value is True

        results = json_results.json_results

        entity_result = None
        for item in results:
            if item.get("Entity") == user_email:
                entity_result = item.get("EntityResult")
                break

        assert entity_result is not None, f"Entity {user_email} not found in results"
        assert "mfa_details" in entity_result
        assert entity_result["mfa_details"]["isMfaRegistered"] is False

        entity = mock_siemplify.target_entities[0]
        assert entity.is_enriched is True
        assert "AAD_mfa_details_isMfaRegistered" in entity.additional_properties
        is_mfa_registered = "AAD_mfa_details_isMfaRegistered"
        assert entity.additional_properties[is_mfa_registered] == "False"

    def test_enrich_user_without_mfa_details(
        self,
        azure_ad_product: AzureADProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: SingleJson,
    ) -> None:
        """Test entity enrichment when MFA details are explicitly not included."""
        action_params["Include MFA Details"] = False
        action_params["Include Last Sign In Details"] = False
        user_email = "AlexW@Contoso.com"

        azure_ad_product.add_user_registration_details(
            user_principal_name=user_email,
            details={"isMfaRegistered": True},
        )

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type="USERUNIQNAME")
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched entities" in action_output.output_message
        assert action_output.result_value is True

        results = json_results.json_results

        entity_result = None
        for item in results:
            if item.get("Entity") == user_email:
                entity_result = item.get("EntityResult")
                break

        assert entity_result is not None, f"Entity {user_email} not found in results"
        assert "mfa_details" not in entity_result

        entity = mock_siemplify.target_entities[0]
        assert entity.is_enriched is True
        assert "AAD_mfa_details_isMfaRegistered" not in entity.additional_properties

    def test_enrich_user_with_sign_in_activity_success(
        self,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: SingleJson,
    ) -> None:
        """Test entity enrichment with sign-in activity details."""
        action_params["Include Last Sign In Details"] = True
        user_email = "AlexW@Contoso.com"

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type="USERUNIQNAME")
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
            mock_response({}),
            mock_response(
                {
                    "id": "user-id-123",
                    "userPrincipalName": user_email,
                    "displayName": "Alex W",
                }
            ),
            mock_response(
                {"signInActivity": {"lastSignInDateTime": "2024-01-01T00:00:00Z"}}
            ),
        ]

        mock_session_instance.post.return_value = mock_response(
            {"access_token": "mock_token"}
        )

        with (
            patch("requests.Session", return_value=mock_session_instance),
            patch(
                (
                    "azure_active_directory.core.AzureADManager"
                    ".requests.Session"
                ),
                return_value=mock_session_instance,
            ),
        ):
            main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched entities" in action_output.output_message

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
        assert "sign_in_details" in entity_result
        assert (
            entity_result["sign_in_details"]["lastSignInDateTime"]
            == "2024-01-01T00:00:00Z"
        )

        entity = mock_siemplify.target_entities[0]
        assert "AAD_sign_in_details_lastSignInDateTime" in entity.additional_properties
        assert (
            entity.additional_properties["AAD_sign_in_details_lastSignInDateTime"]
            == "2024-01-01T00:00:00Z"
        )

    def test_enrich_user_with_sign_in_activity_failure(
        self,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: SingleJson,
    ) -> None:
        """
        Test that the action fails with a descriptive error message when sign-in
        activity API fails due to permission/license issues.
        """
        action_params["Include Last Sign In Details"] = True
        user_email: str = "test@example.com"

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=user_email, entity_type="USERUNIQNAME")
        ]

        mock_session_instance = MagicMock()
        mock_session_instance.headers = {}

        def mock_response(json_data, status_code=200):
            response: MagicMock = MagicMock()
            response.status_code = status_code
            response.json.return_value = json_data
            response.content = json.dumps(json_data).encode("utf-8")
            if status_code != 200:
                from requests.exceptions import HTTPError

                response.raise_for_status.side_effect = HTTPError(
                    f"{status_code} Client Error", response=response
                )
            else:
                response.raise_for_status.return_value = None
            return response

        mock_session_instance.get.side_effect = [
            mock_response({}),
            mock_response(
                {
                    "id": "user-id-123",
                    "userPrincipalName": user_email,
                    "displayName": "Alex W",
                }
            ),
            mock_response(
                {"error": {"message": "Insufficient privileges"}}, status_code=403
            ),
        ]

        mock_session_instance.post.return_value = mock_response(
            {"access_token": "mock_token"}
        )

        with (
            patch("requests.Session", return_value=mock_session_instance),
            patch(
                (
                    "azure_active_directory.core.AzureADManager"
                    ".requests.Session"
                ),
                return_value=mock_session_instance,
            ),
        ):
            main()

        assert action_output.status == EXECUTION_STATE_FAILED
        assert action_output.result_value is False
        assert (
            "The provided credentials don't have permissions to access sign-in activity. "
            in action_output.output_message
        )
