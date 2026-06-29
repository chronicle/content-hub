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

import os
from typing import TYPE_CHECKING
from google_sec_ops_ai_agents.core import consts
from google_sec_ops_ai_agents.core import exceptions
import requests
from google_sec_ops_ai_agents.core.data_models import SessionAuthenticationParameters
from google.auth.transport.requests import AuthorizedSession, Request
from TIPCommon.base.interfaces import Authable
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials, get_impersonated_credentials
import TIPCommon.base.utils

if TYPE_CHECKING:
    import google.auth.credentials


class Authenticator(Authable):
    """Authenticator for Chronicle SOAR."""

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate a session.

        Args:
            params: The session authentication parameters.
        """
        credentials = _create_auth_credentials(params)
        self.session = AuthorizedSession(
            credentials,
            auth_request=_create_auth_request(verify_ssl=params.verify_ssl),
        )
        self.session.verify = params.verify_ssl


def _create_auth_credentials(
    auth_params: SessionAuthenticationParameters,
) -> google.auth.credentials.Credentials:
    """Create authentication credentials.

    Args:
        auth_params: The authentication parameters.

    Returns:
        The authentication credentials.
    """
    if "backstory" in auth_params.api_root:
        raise exceptions.ChronicleInvestigationManagerError(exceptions.INVALID_API_ROOT_ERROR)
    target_scopes = consts.OAUTH_SCOPES
    siem_sa_email = os.environ.get("CHRONICLE_SERVICE_ACCOUNT_EMAIL")
    if siem_sa_email:
        return get_impersonated_credentials(
            target_principal=siem_sa_email,
            target_scopes=target_scopes
        )

    return get_secops_siem_tenant_credentials(
        auth_params.chronicle_soar,
        target_scopes=consts.OAUTH_SCOPES,
        fallback_to_env_email=True,
    )


def _create_auth_request(*, verify_ssl: bool) -> Request:
    """Create an authentication request.

    Args:
        verify_ssl: Whether to verify SSL.

    Returns:
        The authentication request.
    """
    auth_request_session = TIPCommon.base.utils.CreateSession.create_session()
    auth_request_session.verify = verify_ssl
    retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
    auth_request_session.mount("https://", retry_adapter)
    return Request(auth_request_session)
