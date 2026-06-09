from __future__ import annotations

import logging
from typing import Any

import boto3
from google.auth import impersonated_credentials
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import credentials as oauth2_credentials
from google.oauth2 import service_account

from . import consts


class AWSGuardDutyIdentityFederation:
    """Class encapsulating Google Cloud to AWS IAM Role federation."""

    def __init__(
        self,
        role_arn: str | None = None,
        service_account_json: dict[str, Any] | None = None,
        workload_identity_email: str | None = None,
        region_name: str | None = None,
        role_session_name: str = consts.DEFAULT_ROLE_SESSION_NAME,
        siemplify_logger: logging.Logger | None = None,
    ):
        self.role_arn = role_arn
        self.service_account_json = service_account_json
        self.workload_identity_email = workload_identity_email
        self.region_name = region_name
        self.role_session_name = role_session_name
        self.logger = siemplify_logger or logging.getLogger("AWSFederatedAuth")

    def _generate_id_token(
        self,
        source_creds: Any,
        target_principal: str,
        audience: str,
        auth_request: Request,
        error_message: str,
    ) -> str:
        """Generates Google Cloud OIDC ID token using impersonation."""
        if hasattr(source_creds, "with_scopes"):
            source_creds = source_creds.with_scopes([consts.CLOUD_PLATFORM_SCOPE])

        target_creds = impersonated_credentials.Credentials(
            source_credentials=source_creds,
            target_principal=target_principal,
            target_scopes=[consts.CLOUD_PLATFORM_SCOPE],
        )
        creds = impersonated_credentials.IDTokenCredentials(
            target_credentials=target_creds,
            target_audience=audience,
            include_email=True,
        )
        creds.refresh(auth_request)
        if not creds.token:
            raise ValueError(error_message)
        return creds.token

    def get_workload_identity_token(
        self,
        audience: str = consts.STS_AUDIENCE,
        auth_request: Request | None = None,
    ) -> str:
        """Generates a Google OIDC ID token via Workload Identity Impersonation.

        Args:
            audience: The target audience for the generated OIDC token. Defaults
              to STS_AUDIENCE.
            auth_request: The google auth Request object to use. Defaults to
              None.

        Returns:
            The generated Google OIDC ID token.
        """
        if auth_request is None:
            auth_request = Request()

        if not self.workload_identity_email:
            raise ValueError("Workload Identity email must be provided.")

        self.logger.info(
            "Generating OIDC token via Workload Identity Impersonation "
            f"for: {self.workload_identity_email}"
        )
        # Load source credentials if provided.
        if self.service_account_json:
            source_creds = service_account.Credentials.from_service_account_info(
                self.service_account_json
            )
        else:
            # Fall back to Application Default Credentials (ADC).
            source_creds, _ = google.auth.default(scopes=[consts.CLOUD_PLATFORM_SCOPE])

        return self._generate_id_token(
            source_creds=source_creds,
            target_principal=self.workload_identity_email,
            audience=audience,
            auth_request=auth_request,
            error_message=(
                "No token generated for workload identity email: "
                f"{self.workload_identity_email}"
            ),
        )

    def get_impersonated_sa_token(
        self,
        audience: str = consts.STS_AUDIENCE,
        auth_request: Request | None = None,
    ) -> str:
        """Generates a Google OIDC ID token via Service Account Impersonation.

        Args:
            audience: The target audience for the generated OIDC token. Defaults
              to STS_AUDIENCE.
            auth_request: The google auth Request object to use. Defaults to
              None.

        Returns:
            The generated Google OIDC ID token.
        """
        if auth_request is None:
            auth_request = Request()

        if not self.service_account_json:
            raise ValueError("Service Account JSON must be provided.")

        self.logger.info("Generating OIDC token via Service Account Impersonation.")
        source_info = self.service_account_json.get("source_credentials")
        if not source_info:
            raise ValueError(
                "Impersonated credential JSON is missing 'source_credentials'."
            )

        # Load the source credentials.
        if source_info.get("type") == "service_account":
            source_creds = service_account.Credentials.from_service_account_info(
                source_info
            )
        else:
            source_creds = oauth2_credentials.Credentials.from_authorized_user_info(
                source_info
            )

        source_creds.refresh(auth_request)

        # Extract target service account email.
        url = self.service_account_json.get("service_account_impersonation_url", "")
        if not url:
            raise ValueError(
                "Impersonated credential JSON is missing "
                "'service_account_impersonation_url'."
            )
        target_sa = url.split("/")[-1].split(":")[0]

        return self._generate_id_token(
            source_creds=source_creds,
            target_principal=target_sa,
            audience=audience,
            auth_request=auth_request,
            error_message=(
                f"No token generated for impersonated service account: {target_sa}"
            ),
        )

    def get_standard_sa_token(
        self,
        audience: str = consts.STS_AUDIENCE,
        auth_request: Request | None = None,
    ) -> str:
        """Generates a Google OIDC ID token from standard Service Account JSON.

        Args:
            audience: The target audience for the generated OIDC token. Defaults
              to STS_AUDIENCE.
            auth_request: The google auth Request object to use. Defaults to
              None.

        Returns:
            The generated Google OIDC ID token.
        """
        if auth_request is None:
            auth_request = Request()

        if not self.service_account_json:
            raise ValueError("Service Account JSON must be provided.")

        target_audience = self.service_account_json.get("client_id") or audience
        self.logger.info(
            "Generating OIDC token from standard Service Account JSON. "
            f"Target audience: {target_audience}"
        )

        # Load source credentials from service account JSON.
        source_creds = service_account.Credentials.from_service_account_info(
            self.service_account_json
        )

        # Use service account to impersonate itself. This ensures the token is signed by Google
        # (issuer: https://accounts.google.com) rather than being client-side self-signed.
        service_account_email = self.service_account_json.get("client_email")
        if not service_account_email:
            raise ValueError("Service Account JSON is missing 'client_email'.")

        return self._generate_id_token(
            source_creds=source_creds,
            target_principal=service_account_email,
            audience=target_audience,
            auth_request=auth_request,
            error_message="No token generated from standard service account credentials.",
        )

    def get_gcp_oidc_token(
        self,
        audience: str = consts.STS_AUDIENCE,
    ) -> str:
        """Generates a Google OIDC ID token (JWT) for the specified audience.

        Args:
            audience: The target audience for the generated OIDC token. Defaults
              to STS_AUDIENCE.

        Returns:
            The generated Google OIDC ID token.

        Raises:
            ValueError: If neither Service Account JSON nor Workload Identity
              Email is provided.
            """
        auth_request = Request()
        try:
            if self.workload_identity_email:
                return self.get_workload_identity_token(
                    audience=audience,
                    auth_request=auth_request,
                )

            if not self.service_account_json:
                raise ValueError(
                    "Either Service Account JSON or Workload Identity Email "
                    "must be provided."
                )

            cred_type = self.service_account_json.get("type")

            if cred_type == "impersonated_service_account":
                return self.get_impersonated_sa_token(
                    audience=audience,
                    auth_request=auth_request,
                )
            return self.get_standard_sa_token(
                audience=audience,
                auth_request=auth_request,
            )

        except Exception:
            self.logger.exception("Failed to parse or generate token.")
            raise

    def get_web_identity_session(self) -> boto3.Session:
        """Generates a Google OIDC ID token and assumes the AWS Role via STS.

        Returns:
            The authenticated AWS boto3 session.
        """
        if not self.role_arn:
            raise ValueError("Role ARN must be provided to assume a role.")

        token = self.get_gcp_oidc_token()
        sts_client = boto3.client("sts", region_name=self.region_name)

        # In AWS GuardDuty integration, some of the boto3 interactions use stubs.
        # This function generates an active session.
        response = sts_client.assume_role_with_web_identity(
            RoleArn=self.role_arn,
            RoleSessionName=self.role_session_name,
            WebIdentityToken=token,
        )

        credentials = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=self.region_name,
        )
