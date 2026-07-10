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

"""AWS GuardDuty operations functionality."""

from __future__ import annotations

import logging
from typing import Any

import boto3

from . import consts, utils
from .aws_guard_duty_identity_federation import AWSGuardDutyIdentityFederation
from .aws_guard_duty_ops import (
    DetectorOperationsMixin,
    FindingsOperationsMixin,
    IPSetOperationsMixin,
    ThreatIntelSetOperationsMixin,
)
from .aws_guard_duty_parser import AWSGuardDutyParser
from .exceptions import (
    AWSGuardDutyStatusCodeError,
)


class AWSGuardDutyManager(
    DetectorOperationsMixin,
    IPSetOperationsMixin,
    ThreatIntelSetOperationsMixin,
    FindingsOperationsMixin,
):
    """AWS GuardDuty Manager."""

    VALID_STATUS_CODES = (200,)

    def __init__(
        self,
        config: utils.AWSGuardDutyConfig,
        *,
        verify_ssl: bool = False,
        siemplify_logger: logging.Logger | None = None,
    ) -> None:
        """Initialize AWS GuardDuty manager.

        Args:
            config: Integration configuration parameters.
            verify_ssl: Whether to verify SSL connection.
            siemplify_logger: Logger instance.

        Raises:
            ValueError: If required parameters or credentials are not provided.

        """
        self.aws_access_key = config.aws_access_key
        self.aws_secret_key = config.aws_secret_key
        self.aws_default_region = config.aws_default_region
        self.logger = siemplify_logger or logging.getLogger("AWSFederatedAuth")

        if config.role_arn:
            if config.service_account_json or config.workload_identity_email:
                federation = AWSGuardDutyIdentityFederation(
                    config=config,
                    siemplify_logger=self.logger,
                )
                session = federation.get_web_identity_session()
            else:
                if not config.aws_access_key or not config.aws_secret_key:
                    msg = (
                        "AWS Access Key ID and AWS Secret Key are required "
                        "for standard AWS role assumption when GCP OIDC credentials are not provided."
                    )
                    raise ValueError(msg)
                session = self._get_standard_assumed_role_session(
                    role_arn=config.role_arn,
                    aws_access_key=config.aws_access_key,
                    aws_secret_key=config.aws_secret_key,
                    aws_default_region=config.aws_default_region,
                    verify_ssl=verify_ssl,
                )
        else:
            if not config.aws_access_key or not config.aws_secret_key:
                msg = "AWS Access Key ID and AWS Secret Key are required when Role ARN is not provided."
                raise ValueError(msg)
            session = boto3.Session(
                aws_access_key_id=config.aws_access_key,
                aws_secret_access_key=config.aws_secret_key,
                region_name=config.aws_default_region,
            )

        self.client = session.client(
            "guardduty",
            region_name=config.aws_default_region,
            verify=verify_ssl,
        )
        self.parser = AWSGuardDutyParser()

    @staticmethod
    def _get_standard_assumed_role_session(
        role_arn: str,
        aws_access_key: str,
        aws_secret_key: str,
        aws_default_region: str | None,
        *,
        verify_ssl: bool,
    ) -> boto3.Session:
        """Create standard AWS STS AssumeRole session using static keys.

        Args:
            role_arn: The AWS role to assume.
            aws_access_key: AWS Access Key ID.
            aws_secret_key: AWS Secret Access Key.
            aws_default_region: The default region name.
            verify_ssl: Whether to verify SSL.

        Returns:
            The assumed role boto3 Session.

        """
        sts_session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_default_region,
        )
        sts_client = sts_session.client("sts", region_name=aws_default_region, verify=verify_ssl)
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=consts.DEFAULT_ROLE_SESSION_NAME,
        )
        credentials = response["Credentials"]
        return boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=aws_default_region,
        )

    @staticmethod
    def validate_response(response: dict[str, Any], error_msg: str = "An error occurred") -> None:
        """Validate client Security Hub response status code.

        Args:
            response: client Security Hub response.
            error_msg: Error message to display in case of an error.

        Raises:
            AWSGuardDutyStatusCodeError: If status code is not 200.

        """
        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") not in AWSGuardDutyManager.VALID_STATUS_CODES:
            msg = f"{error_msg}. Response: {response}"
            raise AWSGuardDutyStatusCodeError(msg)

    def test_connectivity(self) -> bool:
        """Test connectivity with AWS GuardDuty service.

        Returns:
            True if successfully tested connectivity.

        """
        response = self.client.list_detectors(MaxResults=1)
        self.validate_response(
            response,
            error_msg="Failed to test connectivity with AWS GuardDuty Service.",
        )
        return True


def get_gcp_oidc_token(
    service_account_json: dict[str, Any] | None = None,
    workload_identity_email: str | None = None,
    audience: str = consts.STS_AUDIENCE,
    siemplify_logger: logging.Logger | None = None,
) -> str:
    """Generate a Google OIDC token.

    Args:
        service_account_json: Service account credentials.
        workload_identity_email: Workload identity email.
        audience: Token audience.
        siemplify_logger: Logger instance.

    Returns:
        Google OIDC token string.

    """
    config = utils.AWSGuardDutyConfig(
        aws_access_key=None,
        aws_secret_key=None,
        aws_default_region="us-east-1",
        role_arn=None,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )
    federation = AWSGuardDutyIdentityFederation(
        config=config,
        siemplify_logger=siemplify_logger,
    )
    return federation.get_gcp_oidc_token(audience=audience)


def get_web_identity_session(
    config: utils.AWSGuardDutyConfig,
    role_session_name: str = consts.DEFAULT_ROLE_SESSION_NAME,
    siemplify_logger: logging.Logger | None = None,
) -> boto3.Session:
    """Get an AWS session using OIDC.

    Args:
        config: AWSGuardDutyConfig instance.
        role_session_name: Role session name.
        siemplify_logger: Logger instance.

    Returns:
        AWS assumed role boto3 Session.

    """
    federation = AWSGuardDutyIdentityFederation(
        config=config,
        role_session_name=role_session_name,
        siemplify_logger=siemplify_logger,
    )
    return federation.get_web_identity_session()
