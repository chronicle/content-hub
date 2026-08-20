# Copyright 2025 Google LLC
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

import dataclasses
from typing import TYPE_CHECKING

from requests.adapters import HTTPAdapter
from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from urllib3.util import Retry

from . import api_utils, constants

if TYPE_CHECKING:
    from collections.abc import Mapping

    import requests


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    auth_url: str | None = None


class AuthenticateSession(Authable):
    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate the session.

        Args:
            params: The session authentication parameters.

        """
        self.session = get_authenticated_session(session_parameters=params)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> requests.Session:
    """Get authenticated session with provided configuration parameters.

    Args:
        session_parameters (SessionAuthenticationParameters): Session parameters.

    Returns:
        requests.Session: Authenticated session object.

    """
    session: requests.Session = CreateSession.create_session()
    retry_strategy = Retry(
        total=constants.RETRY_TOTAL_ATTEMPTS,
        backoff_factor=constants.RETRY_BACKOFF_FACTOR,
        status_forcelist=constants.RETRY_STATUS_CODES,
        allowed_methods=frozenset(constants.RETRY_ALLOWED_METHODS),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    _authenticate_session(session, session_parameters=session_parameters)

    return session


def _authenticate_session(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    session.verify: bool = session_parameters.verify_ssl
    bearer_token: str = _generate_token(
        session=session,
        session_parameters=session_parameters,
    )
    session.headers.update({"Authorization": f"Bearer {bearer_token}"})


def get_auth_url(auth_url: str | None = None) -> str:
    """Get the full OAuth token URL from the configured Authentication URL.

    Args:
        auth_url (str | None): The Authentication URL configured in the integration.

    Returns:
        str: The full token URL ending with /oauth/token.

    """
    base_url: str = (auth_url or constants.DEFAULT_AUTH_URL).strip().rstrip("/")
    if base_url.endswith("/oauth/token"):
        return base_url
    return f"{base_url}/oauth/token"


def _generate_token(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> str:
    """Generate a new access token and refresh token using the provided session and parameters.

    Args:
        session (requests.Session): The HTTP session object.
        session_parameters (SessionAuthenticationParameters): The session parameters
        containing client_id, client_secret.

    Returns:
        str: access token.

    """
    auth_payload: Mapping[str, str] = {
        "client_id": session_parameters.client_id,
        "client_secret": session_parameters.client_secret,
        "audience": "wiz-api",
        "grant_type": "client_credentials",
    }
    auth_url: str = get_auth_url(session_parameters.auth_url)
    response: requests.Response = session.post(auth_url, data=auth_payload)
    api_utils.validate_response(response)

    return response.json()["access_token"]
