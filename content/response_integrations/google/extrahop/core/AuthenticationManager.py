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
import dataclasses
import requests

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from extrahop.core import api_utils
from extrahop.core.datamodels import IntegrationParameters


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool


class AuthenticateSession(Authable[IntegrationParameters]):

    def authenticate_session(self, params: IntegrationParameters) -> requests.Session:
        """Get authenticate session with provided configuration parameters.

        Args:
            params (IntegrationParameters): IntegrationParameters object.

        Returns:
            requests.Session: Authenticated session object.
        """
        session_parameters = SessionAuthenticationParameters(
            api_root=params.api_root,
            client_id=params.client_id,
            client_secret=params.client_secret,
            verify_ssl=params.verify_ssl,
        )
        return get_authenticated_session(session_parameters=session_parameters)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> requests.Session:
    """Get authenticated session with provided configuration parameters.

    Args:
        session_parameters (SessionAuthenticationParameters): Session parameters.

    Returns:
        requests.Session: Authenticated session object.
    """
    session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)

    return session


def _authenticate_session(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    session.verify = session_parameters.verify_ssl
    session.auth = (session_parameters.client_id, session_parameters.client_secret)
    access_token = _get_auth_token(
        session=session,
        api_root=session_parameters.api_root,
    )
    session.headers.update({"Authorization": f"Bearer {access_token}"})


def _get_auth_token(session: requests.Session, api_root: str) -> str:
    url = api_utils.get_full_url(api_root=api_root, url_id="token")
    payload = {"grant_type": "client_credentials"}
    response = session.post(url, data=payload)
    api_utils.validate_response(response)

    return response.json().get("access_token")
