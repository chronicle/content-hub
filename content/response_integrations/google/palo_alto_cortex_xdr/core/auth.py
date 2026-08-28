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
import hashlib
import secrets
import string

import arrow
import pytz
import requests

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from ..core.datamodels import IntegrationParameters


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    api_key: str
    api_key_id: str
    verify_ssl: bool


class AuthenticatedSession(Authable[IntegrationParameters]):
    def authenticate_session(self, params: IntegrationParameters) -> requests.Session:
        """Get authenticate session with provided configuration parameters.

        Args:
            params (IntegrationParameters): IntegrationParameters object.

        Returns:
            requests.Session: Authenticated session object.
        """
        session_parameters = SessionAuthenticationParameters(
            api_root=params.api_root,
            api_key=params.api_key,
            api_key_id=params.api_key_id,
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
    session.headers = _calculate_headers(
        api_key=session_parameters.api_key,
        api_key_id=session_parameters.api_key_id,
    )


def _calculate_headers(api_key: str, api_key_id: str) -> dict[str, str]:
    nonce = "".join(
        [secrets.choice(string.ascii_letters + string.digits) for _ in range(64)]
    )
    timestamp = int(arrow.now(pytz.utc).timestamp()) * 1000
    auth_key = f"{api_key}{nonce}{timestamp}"
    auth_key = auth_key.encode("utf-8")
    api_key_hash = hashlib.sha256(auth_key).hexdigest()
    headers = {
        "x-xdr-timestamp": str(timestamp),
        "x-xdr-nonce": nonce,
        "x-xdr-auth-id": str(api_key_id),
        "Authorization": api_key_hash,
    }

    return headers
