from __future__ import annotations

import dataclasses
import json
import os

import pytest
from pytest_mock import MockerFixture

import google.auth.credentials
from google_cloud_armor.core import AuthenticationManager
from google_cloud_armor.core import constants
from google_cloud_armor.core import GoogleCloudArmorManager


# Constants
with open(
    os.path.join(os.path.dirname(__file__), "mock_data.json"), encoding="UTF-8"
) as wf:
    MOCK_DATA = json.load(wf)

STATUS_CODES = {
    "SUCCESS": {"status": 200},
    "BAD_REQUEST": {"status": 400},
    "NOT_FOUND": {"status": 404},
    "CONFLICT": {"status": 409},
}


def mock_request(session, request_string, response_code) -> None:
    session.request.return_value = (
        response_code,
        json.dumps(MOCK_DATA.get(request_string)),
    )


class TestGoogleCloudArmorManager:
    """Unit tests for GoogleCloudArmorManager's functions Integration."""

    def test_test_connectivity_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="list_security_policies",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        result = api_manager.test_connectivity()

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "region",
        [
            constants.DEFAULT_ENVIRONMENT,
            "northamerica-northeast1",
            "us-west1",
        ],
    )
    def test_list_security_policies_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
        region: str,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="list_security_policies",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        policies = api_manager.list_security_policies(region=region)

        # Assert
        assert len(policies) == 1
        assert type(policies[0]).__name__ == "ListSecurityPolicy"
        assert policies[0].name == "abcdef"

    def test_list_security_policies_invalid_failed(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="list_security_policies_failed",
            response_code=STATUS_CODES.get("BAD_REQUEST"),
        )

        # Act
        with pytest.raises(Exception) as error:
            api_manager.list_security_policies()

        # Assert
        assert error.typename == "GoogleCloudArmorError"
        assert (
            "Invalid value at 'header.max_results' (TYPE_UINT32), \"wrong_value\""
            in str(error.value)
        )

    @pytest.mark.parametrize(
        "region",
        [
            constants.DEFAULT_ENVIRONMENT,
            "northamerica-northeast1",
            "us-west1",
        ],
    )
    def test_create_security_policy_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
        region: str,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="create_or_update_security_policy",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        policy = api_manager.create_security_policy(region=region, policy_json={})

        # Assert
        assert type(policy).__name__ == "CreateOrUpdateSecurityPolicy"
        assert policy.policy_id == "5981389776988691495"
        assert policy.status == "RUNNING"

    def test_create_security_policy_invalid_failed(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="create_security_policy_failed",
            response_code=STATUS_CODES.get("CONFLICT"),
        )

        # Act
        with pytest.raises(Exception) as error:
            api_manager.list_security_policies(region=constants.DEFAULT_ENVIRONMENT)

        # Assert
        assert error.typename == "GoogleCloudArmorError"
        assert (
            "The resource "
            "'projects/test-project/global/securityPolicies/testintegration421' "
            "already exists"
        ) in str(error.value)

    @pytest.mark.parametrize(
        "region",
        [
            constants.DEFAULT_ENVIRONMENT,
            "northamerica-northeast1",
            "us-west1",
        ],
    )
    def test_get_security_policy_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
        region: str,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="get_security_policy",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        policy = api_manager.get_security_policy(
            region=region,
            security_policy="abcdef",
        )

        # Assert
        assert type(policy).__name__ == "ListSecurityPolicy"
        assert policy.policy_id == "1552864292462442314"
        assert policy.name == "abcdef"

    def test_get_security_policy_invalid_failed(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="get_security_policy_failed",
            response_code=STATUS_CODES.get("NOT_FOUND"),
        )

        # Act
        with pytest.raises(Exception) as error:
            api_manager.get_security_policy(
                region=constants.DEFAULT_ENVIRONMENT,
                security_policy="abcdef",
            )

        # Assert
        assert error.typename == "GoogleCloudArmorStatusNotFoundError"
        assert (
            "The resource 'projects/test-project/global/securityPolicies/abcdef' "
            "was not found"
        ) in str(error.value)

    @pytest.mark.parametrize(
        "region",
        [
            constants.DEFAULT_ENVIRONMENT,
            "northamerica-northeast1",
            "us-west1",
        ],
    )
    def test_update_security_policy_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
        region: str,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="create_or_update_security_policy",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        policy = api_manager.update_security_policy(
            policy_name="testintegration421",
            region=region,
            policy_json={},
        )

        # Assert
        assert type(policy).__name__ == "CreateOrUpdateSecurityPolicy"
        assert policy.policy_id == "5981389776988691495"
        assert policy.status == "RUNNING"

    def test_update_security_policy_invalid_failed(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="update_security_policy_failed",
            response_code=STATUS_CODES.get("CONFLICT"),
        )

        # Act
        with pytest.raises(Exception) as error:
            api_manager.list_security_policies(region=constants.DEFAULT_ENVIRONMENT)

        # Assert
        assert error.typename == "GoogleCloudArmorError"
        assert (
            "Invalid value for field 'resource.rules[1].priority': '100'. "
            "Cannot have rules with the same priorities."
        ) in str(error.value)

    @pytest.mark.parametrize(
        "region",
        [
            constants.DEFAULT_ENVIRONMENT,
            "northamerica-northeast1",
            "us-west1",
        ],
    )
    def test_add_rule_to_security_policy_valid_success(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
        region: str,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="create_or_update_security_policy",
            response_code=STATUS_CODES.get("SUCCESS"),
        )

        # Act
        policy = api_manager.add_rule_to_security_policy(
            policy_name="testintegration421",
            region=region,
            policy_json={},
        )

        # Assert
        assert type(policy).__name__ == "CreateOrUpdateSecurityPolicy"
        assert policy.policy_id == "5981389776988691495"
        assert policy.status == "RUNNING"

    def test_add_rule_to_security_policy_invalid_failed(
        self,
        api_manager: GoogleCloudArmorManager.ApiManager,
    ) -> None:
        # Arrange
        mock_request(
            session=api_manager.session,
            request_string="add_rule_to_security_policy_failed",
            response_code=STATUS_CODES.get("BAD_REQUEST"),
        )

        # Act
        with pytest.raises(Exception) as error:
            api_manager.add_rule_to_security_policy(
                policy_name="testintegration421",
                region=constants.DEFAULT_ENVIRONMENT,
                policy_json={},
            )

        # Assert
        assert error.typename == "GoogleCloudArmorError"
        assert "Invalid value for field 'resource.rules[0]'" in str(error.value)


class TestAuthenticationManager:
    """Unit tests for AuthenticationManager's functions Integration."""

    def test_get_authentication_credentials_or_raise_error_valid_success(
        self,
        mocker: MockerFixture,
        auth_params: AuthenticationManager.SessionAuthenticationParameters,
    ):
        # Arrange
        auth_params.user_service_account = None
        auth_params.workload_identity_email = "mocker@email.com"
        mocker.patch(
            "TIPCommon.rest.auth.build_credentials_from_sa",
            return_value=mocker.Mock(),
        )

        # Act
        AuthenticationManager.get_authentication_credentials_or_raise_error(
            session_parameters=auth_params
        )

    def test_get_authentication_credentials_or_raise_error_invalid_failed(
        self,
        auth_params: AuthenticationManager.SessionAuthenticationParameters,
    ) -> None:
        # Arrange
        auth_params.user_service_account = None
        auth_params.workload_identity_email = None

        # Act
        with pytest.raises(Exception) as error:
            AuthenticationManager.get_authentication_credentials_or_raise_error(
                session_parameters=auth_params
            )

        # Assert
        assert error.typename == "GoogleCloudArmorValidationError"
        assert (
            "Please fill either 'Service Account Json File Content', "
            "'Workload Identity Email' or all other parameters"
        ) in str(error.value)

    def test_get_authentication_credentials_or_raise_error_with_wi_invalid_failed(
        self,
        mocker: MockerFixture,
        auth_params: AuthenticationManager.SessionAuthenticationParameters,
    ) -> None:
        # Arrange
        auth_params.user_service_account = None
        auth_params.workload_identity_email = "mocker@email.com"
        mock_sa = mocker.Mock()
        mock_sa.side_effect = google.auth.exceptions.RefreshError("Error occurred")
        mocker.patch(
            "TIPCommon.rest.auth.build_credentials_from_sa",
            mock_sa,
        )

        # Act
        with pytest.raises(Exception) as error:
            AuthenticationManager.get_authentication_credentials_or_raise_error(
                session_parameters=auth_params
            )

        # Assert
        assert error.typename == "GoogleCloudArmorError"
        assert "Impersonation is not allowed for the provided service" in str(
            error.value
        )

    def test_create_resource_name_valid_success(
        self,
        api_params: GoogleCloudArmorManager.ApiParameters,
    ) -> None:
        # Arrange
        api_params.project_id = "mock_id"
        resource_params = dataclasses.asdict(api_params)
        resource_params.pop("api_root")

        # Act
        result = AuthenticationManager.create_resource_name(**resource_params)

        # Assert
        assert result == api_params.project_id
