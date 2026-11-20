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

from google.auth.transport.requests import AuthorizedSession, Request
from TIPCommon.base.utils import CreateSession
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials

from .constants import CLOUD_PLATFORM_SCOPE, GCP_PROJECT_ID_ENV_VAR

if TYPE_CHECKING:
    import google.auth.credentials
    import TIPCommon.types


def get_p4sa_credentials(
    chronicle_soar: TIPCommon.types.ChronicleSOAR,
) -> google.auth.credentials.Credentials:
    """Retrieve short-lived SIEM tenant credentials using the P4SA.

    Args:
        chronicle_soar: The SOAR SDK object used to read tenant auth context.

    Returns:
        The short-lived Google auth credentials for the SIEM tenant.

    """
    project_id = os.getenv(GCP_PROJECT_ID_ENV_VAR)
    return get_secops_siem_tenant_credentials(
        chronicle_soar=chronicle_soar,
        target_scopes=[CLOUD_PLATFORM_SCOPE],
        quota_project_id=project_id,
    )


def refresh_p4sa_credentials(
    chronicle_soar: TIPCommon.types.ChronicleSOAR,
    *,
    verify_ssl: bool = True,
) -> None:
    """Retrieve and refresh SIEM tenant P4SA credentials to verify connectivity.

    Args:
        chronicle_soar: The SOAR SDK object used to read tenant auth context.
        verify_ssl: Whether to verify SSL certificates during token refresh.

    """
    credentials = get_p4sa_credentials(chronicle_soar)
    with CreateSession.create_session() as auth_session:
        auth_session.verify = verify_ssl
        credentials.refresh(Request(session=auth_session))


def create_p4sa_authorized_session(
    chronicle_soar: TIPCommon.types.ChronicleSOAR,
    *,
    verify_ssl: bool = True,
) -> AuthorizedSession:
    """Create and configure an AuthorizedSession authenticated via P4SA.

    Args:
        chronicle_soar: The SOAR SDK object used to read tenant auth context.
        verify_ssl: Whether to verify SSL certificates on auth and API requests.

    Returns:
        The configured authorized HTTP session.

    """
    credentials = get_p4sa_credentials(chronicle_soar)
    auth_session = CreateSession.create_session()
    auth_session.verify = verify_ssl
    http_client = AuthorizedSession(credentials, auth_request=Request(session=auth_session))
    http_client.verify = verify_ssl
    return http_client
