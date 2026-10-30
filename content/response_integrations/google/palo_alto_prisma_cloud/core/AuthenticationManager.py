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
import copy
import dataclasses
import requests
from . import api_utils
from . import constants


@dataclasses.dataclass
class SessionAuthenticationParameters:
    api_root: str
    access_key_id: str
    secret_access_key: str
    verify_ssl: bool


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> requests.Session:
    """Get an authenticated requests.Session.

    This function creates a new requests.Session, authenticates it using the provided
    session parameters, and returns the authenticated session.

    Args:
        session_parameters (SessionAuthenticationParameters): The authentication
            parameters for configuring the session.

    Returns:
        requests.Session: An authenticated requests.Session.
    """
    session = requests.Session()
    _authenticate_session(session, session_parameters=session_parameters)

    return session


def _authenticate_session(
    session: requests.Session, session_parameters: SessionAuthenticationParameters
) -> None:
    session.verify = session_parameters.verify_ssl
    access_token = generate_token(
        session=session, session_parameters=session_parameters
    )
    session.headers.update({"Authorization": f"Bearer {access_token}"})


def generate_token(
    session: requests.Session, session_parameters: SessionAuthenticationParameters
) -> str:
    """Generate a token.

    Args:
        session (requests.Session): The session to use for authentication.
        session_parameters (SessionAuthenticationParameters):
            The parameters for session authentication.

    Returns:
        str: The generated token.
    """
    payload = copy.deepcopy(constants.TOKEN_PAYLOAD_FROM_SECRET)
    payload["username"] = session_parameters.access_key_id
    payload["password"] = session_parameters.secret_access_key
    url = api_utils.get_full_url(
        api_root=session_parameters.api_root,
        endpoint_id="login",
        endpoints=constants.ENDPOINTS,
    )
    response = session.post(url, json=payload)
    api_utils.validate_response(response)

    return response.json().get("token")
