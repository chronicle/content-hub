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

from google.auth import iam
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from TIPCommon.rest.auth import build_credentials_from_sa, get_auth_request
from TIPCommon.rest.gcp import get_workload_sa_email
from TIPCommon.utils import is_empty_string_or_none

from .consts import OAUTH_SCOPES
from .exceptions import GoogleCloudAuthenticationError


class AuthManager:
    def __init__(
        self,
        service_account_creds: str | dict | None,
        workload_identity_email: str | None,
        delegated_email: str | None,
        *,
        verify_ssl: bool,
    ) -> None:
        """Initialize the AuthManager.

        Args:
            service_account_creds: The service account credentials as a string,
                dict, or file path.
            workload_identity_email: The email of the service account to impersonate.
            delegated_email: The email of the user to impersonate.
            verify_ssl: Whether to verify SSL certificates.

        Raises:
            GoogleCloudAuthenticationError: If authentication or impersonation fails.

        """
        self.verify_ssl = verify_ssl

        service_account_json = service_account_creds
        if not is_empty_string_or_none(service_account_creds) and not isinstance(
            service_account_creds, dict
        ):
            service_account_json = json.loads(service_account_creds)

        try:
            credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=OAUTH_SCOPES,
                verify_ssl=verify_ssl,
            )

            # Create an IAM signer using the SA credentials.
            signer = iam.Signer(
                get_auth_request(verify_ssl),
                credentials,
                credentials.service_account_email,
            )

            # Create OAuth 2.0 Service Account credentials using the IAM-based
            # signer and the bootstrap_credential's service account email.
            # Impersonate the given subject.
            self.credentials = service_account.Credentials(
                signer,
                credentials.service_account_email,
                "https://accounts.google.com/o/oauth2/token",
                scopes=OAUTH_SCOPES,
                subject=delegated_email,
            )
        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            msg = (
                "Impersonation is not allowed for the provided service account "
                f"{workload_identity_email}. Please add the 'Service Account "
                "Token Creator' role to the service account: "
                f"{workload_sa_email}"
            )
            raise GoogleCloudAuthenticationError(msg) from e

    def prepare_session(self) -> AuthorizedSession:
        """Prepare an authorized session for API requests.

        Returns:
            An AuthorizedSession object.

        """
        session = AuthorizedSession(
            self.credentials, auth_request=get_auth_request(self.verify_ssl)
        )
        session.verify = self.verify_ssl
        return session
