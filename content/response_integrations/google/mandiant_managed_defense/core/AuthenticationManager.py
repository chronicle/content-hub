from __future__ import annotations

import dataclasses
import requests
from mandiant_managed_defense.core import api_utils
from mandiant_managed_defense.core.exceptions import MandiantMDException


@dataclasses.dataclass
class SessionAuthenticationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool


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
    access_token = generate_access_token(auth_params)

    if not access_token:
        raise MandiantMDException("Failed to generate authentication token.")

    session.headers.update({"Authorization": f"Bearer {access_token}"})
    return session


def generate_access_token(auth_params: SessionAuthenticationParameters) -> str:
    """Generate access token for authentication

    Args:
        auth_params (auth_manager.SessionAuthenticationParameters): auth params object

    Returns:
        str: access token
    """
    url = api_utils.get_full_url(
        api_root=auth_params.api_root, endpoint_id="generate_token"
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = "grant_type=client_credentials"

    session = requests.Session()
    session.auth = (auth_params.client_id, auth_params.client_secret)
    session.verify = auth_params.verify_ssl
    response = session.post(url, headers=headers, data=payload)
    api_utils.validate_response(response)
    return response.json().get("access_token", "")
