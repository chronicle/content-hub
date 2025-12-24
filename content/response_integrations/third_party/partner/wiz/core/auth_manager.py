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

from typing import TYPE_CHECKING
import dataclasses

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession

from . import api_utils
from . import constants

if TYPE_CHECKING:
    from collections.abc import Mapping

    import requests


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool


class AuthenticateSession(Authable):
    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
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


def _generate_token(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> str:
    """
    Generate a new access token and refresh token using the provided session and
    parameters.

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
    response: requests.Response = session.post(constants.AUTH_URL, data=auth_payload)
    api_utils.validate_response(response)

    return response.json()["access_token"]
