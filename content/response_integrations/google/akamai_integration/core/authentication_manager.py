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
from akamai.edgegrid import EdgeGridAuth

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession

from akamai_integration.core.datamodels import IntegrationParameters


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    client_token: str
    client_secret: str
    access_token: str
    verify_ssl: bool


class AuthenticateSession(Authable[IntegrationParameters]):
    def authenticate_session(self, params: IntegrationParameters) -> requests.Session:
        """Get authenticate session with provided configuration parameters.

        Args:
            params (IntegrationParameters): IntegrationParameters object.

        Returns:
            requests.Session: Authenticated session object.

        """
        session_parameters: SessionAuthenticationParameters = (
            SessionAuthenticationParameters(
                api_root=params.api_root,
                client_token=params.client_token,
                client_secret=params.client_secret,
                access_token=params.access_token,
                verify_ssl=params.verify_ssl,
            )
        )
        return get_authenticated_session(session_parameters=session_parameters)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> requests.Session:
    """Get authenticated session."""
    session: requests.Session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)

    return session


def _authenticate_session(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    session.verify = session_parameters.verify_ssl
    session.auth = EdgeGridAuth(
        client_token=session_parameters.client_token,
        client_secret=session_parameters.client_secret,
        access_token=session_parameters.access_token,
    )
