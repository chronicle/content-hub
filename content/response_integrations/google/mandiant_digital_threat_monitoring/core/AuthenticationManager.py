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
from . import api_utils
from .constants import ENDPOINTS
from .exceptions import (
    MandiantDTMException,
    MandiantDTMInvalidParameters,
    MandiantDTMInvalidUnicodeKeyError,
)


@dataclasses.dataclass
class SessionAuthenticationParameters:
    api_root: str
    verify_ssl: bool
    client_id: str = None
    client_secret: str = None
    gti_api_key: str = None


def get_authenticated_session(
    auth_params: SessionAuthenticationParameters,
) -> requests.Session:
    """Get authenticated session based on auth method and auth params

    Args:
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        requests.Session: requests.Session object
    """
    session = requests.Session()
    session.verify = auth_params.verify_ssl

    _validate_keys(auth_params)

    if auth_params.gti_api_key:
        session.auth = None
        session.headers.update(
            {"Accept": "application/json", "x-apikey": auth_params.gti_api_key}
        )
        return session

    access_token = generate_access_token(session, auth_params)
    if not access_token:
        raise MandiantDTMException("Failed to generate authentication token.")

    session.auth = None
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    return session


def _validate_keys(auth_params: SessionAuthenticationParameters) -> None:
    """Validate that the provided keys do not contain Unicode characters
    and ensure that at least one of the required keys is provided.
    """

    if (
        not auth_params.client_id
        and not auth_params.client_secret
        and not auth_params.gti_api_key
    ):
        raise MandiantDTMInvalidParameters(
            "Either 'Client ID' + 'Client Secret' or 'GTI API Key' "
            "should be provided. Make sure that the correct API root "
            "is provided as well."
        )

    keys = [auth_params.client_id, auth_params.client_secret, auth_params.gti_api_key]
    for key in keys:
        if key and any(ord(char) > 127 for char in key):
            raise MandiantDTMInvalidUnicodeKeyError(
                "Please verify the 'Client ID,' 'Client Secret,' or 'GTI API Key'"
                " credentials."
            )


def generate_access_token(
    session: requests.Session, auth_params: SessionAuthenticationParameters
) -> str:
    """Generate access token for authentication

    Args:
        session (requests.Session): requests.Session object
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        str: access token
    """
    url = api_utils.get_full_url(
        api_root=auth_params.api_root, endpoint=ENDPOINTS["generate_token"]
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = "grant_type=client_credentials"
    session.auth = (auth_params.client_id, auth_params.client_secret)

    response = session.post(url, headers=headers, data=payload)
    api_utils.validate_response(response)
    return response.json().get("access_token", "")
