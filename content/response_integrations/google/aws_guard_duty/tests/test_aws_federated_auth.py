from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.AWSGuardDutyIdentityFederation import AWSGuardDutyIdentityFederation
from core.AWSGuardDutyManager import AWSGuardDutyManager


# ==============================================================================
# Helper tests (AWSGuardDutyIdentityFederation.py functional split methods)
# ==============================================================================


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch(
    "core.AWSGuardDutyIdentityFederation.service_account.Credentials.from_service_account_info"
)
def test_get_gcp_oidc_token_with_service_account_json_content(
    mock_from_info: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test generating OIDC token programmatically from direct GCP service account JSON dictionary content."""
    mock_creds = MagicMock()
    mock_creds.token = "mock-jwt-token-from-json-content"
    mock_id_token_creds.return_value = mock_creds

    mock_target_creds = MagicMock()
    mock_impersonated_creds.return_value = mock_target_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_from_info.return_value = mock_source_creds

    fake_json_content = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key": "fake-key",
        "client_id": "mock-client-id-12345",
        "client_email": "sa-email@fake-project.iam.gserviceaccount.com",
    }

    federation = AWSGuardDutyIdentityFederation(
        service_account_json=fake_json_content,
    )
    token = federation.get_gcp_oidc_token(
        audience="https://sts.amazonaws.com",
    )

    mock_from_info.assert_called_once_with(fake_json_content)
    mock_impersonated_creds.assert_called_once()
    call_kwargs = mock_impersonated_creds.call_args.kwargs
    assert call_kwargs["source_credentials"] == mock_source_creds
    assert (
        call_kwargs["target_principal"]
        == "sa-email@fake-project.iam.gserviceaccount.com"
    )

    mock_id_token_creds.assert_called_once_with(
        target_credentials=mock_target_creds,
        target_audience="mock-client-id-12345",
        include_email=True,
    )
    mock_creds.refresh.assert_called_once()
    assert token == "mock-jwt-token-from-json-content"


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch("google.auth.default")
def test_get_gcp_oidc_token_with_workload_identity_email_only(
    mock_google_auth_default: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test OIDC token generation via workload identity impersonation fallback."""
    mock_creds = MagicMock()
    mock_creds.token = "mock-workload-identity-jwt"
    mock_id_token_creds.return_value = mock_creds

    mock_target_creds = MagicMock()
    mock_impersonated_creds.return_value = mock_target_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_google_auth_default.return_value = (mock_source_creds, "project-id")

    federation = AWSGuardDutyIdentityFederation(
        service_account_json=None,
        workload_identity_email="target-sa@project-id.iam.gserviceaccount.com",
    )
    token = federation.get_gcp_oidc_token(
        audience="https://sts.amazonaws.com",
    )

    mock_google_auth_default.assert_called_once_with(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    mock_impersonated_creds.assert_called_once()
    call_kwargs = mock_impersonated_creds.call_args.kwargs
    assert call_kwargs["source_credentials"] == mock_source_creds
    assert (
        call_kwargs["target_principal"]
        == "target-sa@project-id.iam.gserviceaccount.com"
    )

    mock_id_token_creds.assert_called_once_with(
        target_credentials=mock_target_creds,
        target_audience="https://sts.amazonaws.com",
        include_email=True,
    )
    mock_creds.refresh.assert_called_once()
    assert token == "mock-workload-identity-jwt"


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch("google.auth.default")
def test_get_workload_identity_token(
    mock_google_auth_default: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test direct call to get_workload_identity_token."""
    mock_creds = MagicMock()
    mock_creds.token = "workload-identity-jwt"
    mock_id_token_creds.return_value = mock_creds

    mock_target_creds = MagicMock()
    mock_impersonated_creds.return_value = mock_target_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_google_auth_default.return_value = (mock_source_creds, "project-id")

    federation = AWSGuardDutyIdentityFederation(
        workload_identity_email="target-sa@project-id.iam.gserviceaccount.com",
    )
    token = federation.get_workload_identity_token(
        audience="https://sts.amazonaws.com",
    )

    mock_google_auth_default.assert_called_once_with(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    mock_impersonated_creds.assert_called_once()
    call_kwargs = mock_impersonated_creds.call_args.kwargs
    assert call_kwargs["source_credentials"] == mock_source_creds
    assert (
        call_kwargs["target_principal"]
        == "target-sa@project-id.iam.gserviceaccount.com"
    )

    mock_id_token_creds.assert_called_once_with(
        target_credentials=mock_target_creds,
        target_audience="https://sts.amazonaws.com",
        include_email=True,
    )
    mock_creds.refresh.assert_called_once()
    assert token == "workload-identity-jwt"


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch(
    "core.AWSGuardDutyIdentityFederation.service_account.Credentials.from_service_account_info"
)
def test_get_standard_sa_token(
    mock_from_info: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test direct call to get_standard_sa_token."""
    mock_creds = MagicMock()
    mock_creds.token = "standard-sa-jwt"
    mock_id_token_creds.return_value = mock_creds

    mock_target_creds = MagicMock()
    mock_impersonated_creds.return_value = mock_target_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_from_info.return_value = mock_source_creds

    fake_json_content = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key": "fake-key",
        "client_id": "mock-client-id-12345",
        "client_email": "sa-email@fake-project.iam.gserviceaccount.com",
    }

    federation = AWSGuardDutyIdentityFederation(
        service_account_json=fake_json_content,
    )
    token = federation.get_standard_sa_token(
        audience="https://sts.amazonaws.com",
    )

    mock_from_info.assert_called_once_with(fake_json_content)
    mock_impersonated_creds.assert_called_once()
    call_kwargs = mock_impersonated_creds.call_args.kwargs
    assert call_kwargs["source_credentials"] == mock_source_creds
    assert (
        call_kwargs["target_principal"]
        == "sa-email@fake-project.iam.gserviceaccount.com"
    )

    mock_id_token_creds.assert_called_once_with(
        target_credentials=mock_target_creds,
        target_audience="mock-client-id-12345",
        include_email=True,
    )
    mock_creds.refresh.assert_called_once()
    assert token == "standard-sa-jwt"


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch(
    "core.AWSGuardDutyIdentityFederation.service_account.Credentials.from_service_account_info"
)
def test_get_impersonated_sa_token(
    mock_from_info: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test direct call to get_impersonated_sa_token."""
    mock_creds = MagicMock()
    mock_creds.token = "impersonated-sa-jwt"
    mock_id_token_creds.return_value = mock_creds

    mock_target_creds = MagicMock()
    mock_impersonated_creds.return_value = mock_target_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_from_info.return_value = mock_source_creds

    fake_json_content = {
        "type": "impersonated_service_account",
        "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/target-sa@project-id.iam.gserviceaccount.com:generateIdToken",
        "source_credentials": {
            "type": "service_account",
            "project_id": "fake-project",
            "private_key": "fake-key",
        },
    }

    federation = AWSGuardDutyIdentityFederation(
        service_account_json=fake_json_content,
    )
    token = federation.get_impersonated_sa_token(
        audience="https://sts.amazonaws.com",
    )

    mock_from_info.assert_called_once_with(fake_json_content["source_credentials"])
    mock_impersonated_creds.assert_called_once()
    call_kwargs = mock_impersonated_creds.call_args.kwargs
    assert call_kwargs["source_credentials"] == mock_source_creds
    assert (
        call_kwargs["target_principal"]
        == "target-sa@project-id.iam.gserviceaccount.com"
    )

    mock_id_token_creds.assert_called_once_with(
        target_credentials=mock_target_creds,
        target_audience="https://sts.amazonaws.com",
        include_email=True,
    )
    mock_creds.refresh.assert_called_once()
    assert token == "impersonated-sa-jwt"


# ==============================================================================
# Validation failure tests
# ==============================================================================


def test_get_workload_identity_token_missing_email() -> None:
    """Test that Value error is raised when workload identity email is missing."""
    federation = AWSGuardDutyIdentityFederation(
        workload_identity_email=None,
    )
    with pytest.raises(ValueError, match="Workload Identity email must be provided."):
        federation.get_workload_identity_token()


def test_get_standard_sa_token_missing_json() -> None:
    """Test that Value error is raised when Service Account JSON is missing."""
    federation = AWSGuardDutyIdentityFederation(
        service_account_json=None,
    )
    with pytest.raises(ValueError, match="Service Account JSON must be provided."):
        federation.get_standard_sa_token()


@patch("google.auth.impersonated_credentials.Credentials")
@patch(
    "core.AWSGuardDutyIdentityFederation.service_account.Credentials.from_service_account_info"
)
def test_get_standard_sa_token_missing_client_email(
    mock_from_info: MagicMock,
    mock_impersonated_creds: MagicMock,
) -> None:
    """Test that Value error is raised when Service Account JSON is missing client_email."""
    fake_json_content = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key": "fake-key",
        "client_id": "mock-client-id-12345",
        # "client_email" is missing
    }
    federation = AWSGuardDutyIdentityFederation(
        service_account_json=fake_json_content,
    )
    with pytest.raises(
        ValueError, match="Service Account JSON is missing 'client_email'."
    ):
        federation.get_standard_sa_token()


@patch("google.auth.impersonated_credentials.IDTokenCredentials")
@patch("google.auth.impersonated_credentials.Credentials")
@patch(
    "core.AWSGuardDutyIdentityFederation.service_account.Credentials.from_service_account_info"
)
def test_get_standard_sa_token_no_token_generated(
    mock_from_info: MagicMock,
    mock_impersonated_creds: MagicMock,
    mock_id_token_creds: MagicMock,
) -> None:
    """Test that Value error is raised when OIDC token is not generated successfully."""
    mock_creds = MagicMock()
    mock_creds.token = None  # No token generated
    mock_id_token_creds.return_value = mock_creds

    mock_source_creds = MagicMock()
    mock_source_creds.with_scopes.return_value = mock_source_creds
    mock_from_info.return_value = mock_source_creds

    fake_json_content = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key": "fake-key",
        "client_id": "mock-client-id-12345",
        "client_email": "sa-email@fake-project.iam.gserviceaccount.com",
    }
    federation = AWSGuardDutyIdentityFederation(
        service_account_json=fake_json_content,
    )
    with pytest.raises(
        ValueError,
        match="No token generated from standard service account credentials.",
    ):
        federation.get_standard_sa_token()


# ==============================================================================
# Manager Integration tests (AWSGuardDutyManager.py)
# ==============================================================================


@patch("core.AWSGuardDutyManager.boto3.Session")
def test_guardduty_manager_static_credentials_success(
    mock_session_class: MagicMock,
) -> None:
    """Test manager initialization with valid static credentials."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    manager = AWSGuardDutyManager(
        aws_access_key="ASIAEXAMPLE",
        aws_secret_key="wJalrXUtnFEMI/K7MDENG",
        aws_default_region="us-east-1",
        role_arn=None,
    )

    mock_session_class.assert_called_once_with(
        aws_access_key_id="ASIAEXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG",
        region_name="us-east-1",
    )
    mock_session.client.assert_called_once_with(
        "guardduty", region_name="us-east-1", verify=False
    )
    assert manager.client == mock_session.client.return_value


def test_guardduty_manager_static_credentials_missing_keys() -> None:
    """Test that manager initialization throws ValueError when static keys are missing."""
    with pytest.raises(
        ValueError, match="AWS Access Key ID and AWS Secret Key are required"
    ):
        AWSGuardDutyManager(
            aws_access_key=None,
            aws_secret_key=None,
            aws_default_region="us-east-1",
            role_arn=None,
        )


@patch("core.AWSGuardDutyManager.boto3.client")
@patch(
    "core.AWSGuardDutyIdentityFederation.AWSGuardDutyIdentityFederation.get_gcp_oidc_token"
)
@patch("core.AWSGuardDutyManager.boto3.Session")
def test_guardduty_manager_federation_session_creation(
    mock_session_class: MagicMock,
    mock_get_oidc_token: MagicMock,
    mock_boto3_client: MagicMock,
) -> None:
    """Test manager initialization using AWS STS Web Identity federation via Service Account JSON path."""
    mock_get_oidc_token.return_value = "fake-gcp-oidc-jwt"

    mock_sts = MagicMock()
    mock_boto3_client.return_value = mock_sts
    mock_sts.assume_role_with_web_identity.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIAFEDERATEDKEY",
            "SecretAccessKey": "fake-secret-key",
            "SessionToken": "fake-session-token",
        }
    }

    mock_federated_session = MagicMock()
    mock_session_class.return_value = mock_federated_session

    fake_json_content = {
        "type": "service_account",
        "project_id": "fake-project",
        "private_key": "fake-key",
    }

    manager = AWSGuardDutyManager(
        aws_access_key=None,
        aws_secret_key=None,
        aws_default_region="us-west-2",
        role_arn="arn:aws:iam::123456789012:role/SOAR-OIDC-Role",
        service_account_json=fake_json_content,
    )

    # Verify OIDC Token generation was called
    mock_get_oidc_token.assert_called_once_with()

    # Verify STS Role Assumption was called
    mock_boto3_client.assert_called_once_with("sts", region_name="us-west-2")
    mock_sts.assume_role_with_web_identity.assert_called_once_with(
        RoleArn="arn:aws:iam::123456789012:role/SOAR-OIDC-Role",
        RoleSessionName="SOAR-GuardDuty-Session",
        WebIdentityToken="fake-gcp-oidc-jwt",
    )

    # Verify session was created from temporary credentials
    mock_session_class.assert_called_once_with(
        aws_access_key_id="ASIAFEDERATEDKEY",
        aws_secret_access_key="fake-secret-key",
        aws_session_token="fake-session-token",
        region_name="us-west-2",
    )
    assert manager.client == mock_federated_session.client.return_value


@patch("core.AWSGuardDutyManager.boto3.client")
@patch(
    "core.AWSGuardDutyIdentityFederation.AWSGuardDutyIdentityFederation.get_gcp_oidc_token"
)
@patch("core.AWSGuardDutyManager.boto3.Session")
def test_guardduty_manager_workload_identity_success(
    mock_session_class: MagicMock,
    mock_get_oidc_token: MagicMock,
    mock_boto3_client: MagicMock,
) -> None:
    """Test manager setup using Workload Identity Email authentication."""
    mock_get_oidc_token.return_value = "fake-gcp-oidc-jwt"

    mock_sts = MagicMock()
    mock_boto3_client.return_value = mock_sts
    mock_sts.assume_role_with_web_identity.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIAFEDERATEDKEY",
            "SecretAccessKey": "fake-secret-key",
            "SessionToken": "fake-session-token",
        }
    }

    mock_federated_session = MagicMock()
    mock_session_class.return_value = mock_federated_session

    manager = AWSGuardDutyManager(
        aws_access_key=None,
        aws_secret_key=None,
        aws_default_region="us-west-2",
        role_arn="arn:aws:iam::123456789012:role/SOAR-OIDC-Role",
        workload_identity_email="target-sa@project-id.iam.gserviceaccount.com",
    )

    # Verify OIDC Token generation was called
    mock_get_oidc_token.assert_called_once_with()

    # Verify STS Role Assumption was called
    mock_boto3_client.assert_called_once_with("sts", region_name="us-west-2")
    mock_sts.assume_role_with_web_identity.assert_called_once_with(
        RoleArn="arn:aws:iam::123456789012:role/SOAR-OIDC-Role",
        RoleSessionName="SOAR-GuardDuty-Session",
        WebIdentityToken="fake-gcp-oidc-jwt",
    )

    assert manager.client == mock_federated_session.client.return_value


@patch("core.AWSGuardDutyManager.boto3.Session")
def test_guardduty_manager_standard_assume_role_success(
    mock_session_class: MagicMock,
) -> None:
    """Test manager setup using standard STS assume_role fallback when role_arn is present but GCP credentials are not."""
    # We expect two Session instances to be created:
    # 1. sts_session = Session(aws_access_key_id, aws_secret_access_key, region_name)
    # 2. assumed_session = Session(aws_access_key_id, aws_secret_access_key, aws_session_token, region_name)
    mock_sts_session = MagicMock()
    mock_assumed_session = MagicMock()
    mock_session_class.side_effect = [mock_sts_session, mock_assumed_session]

    mock_sts_client = MagicMock()
    mock_sts_session.client.return_value = mock_sts_client
    mock_sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIAASSUMEDKEY",
            "SecretAccessKey": "assumed-secret",
            "SessionToken": "assumed-session-token",
        }
    }

    manager = AWSGuardDutyManager(
        aws_access_key="ASIAEXAMPLE",
        aws_secret_key="wJalrXUtnFEMI/K7MDENG",
        aws_default_region="us-east-1",
        role_arn="arn:aws:iam::123456789012:role/StandardAssumeRole",
        service_account_json=None,
        workload_identity_email=None,
    )

    # Verify first Session was initialized with input static keys
    mock_session_class.assert_any_call(
        aws_access_key_id="ASIAEXAMPLE",
        aws_secret_access_key="wJalrXUtnFEMI/K7MDENG",
        region_name="us-east-1",
    )
    # Verify STS assume_role was called
    mock_sts_session.client.assert_called_once_with(
        "sts", region_name="us-east-1", verify=False
    )
    mock_sts_client.assume_role.assert_called_once_with(
        RoleArn="arn:aws:iam::123456789012:role/StandardAssumeRole",
        RoleSessionName="SOAR-GuardDuty-Session",
    )
    # Verify second Session was initialized with temporary credentials from STS response
    mock_session_class.assert_any_call(
        aws_access_key_id="ASIAASSUMEDKEY",
        aws_secret_access_key="assumed-secret",
        aws_session_token="assumed-session-token",
        region_name="us-east-1",
    )
    assert manager.client == mock_assumed_session.client.return_value
