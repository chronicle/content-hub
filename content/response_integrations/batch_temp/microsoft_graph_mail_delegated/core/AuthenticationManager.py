from __future__ import annotations

from collections import namedtuple
import copy
import dataclasses

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from . import api_utils
from . import constants
from .datamodels import IntegrationParameters


Tokens = namedtuple("Tokens", ["access_token", "refresh_token"])


@dataclasses.dataclass
class SessionAuthenticationParameters:
    azure_ad_endpoint: str
    client_id: str
    client_secret: str
    tenant: str
    refresh_token: str
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
            azure_ad_endpoint=params.azure_ad_endpoint,
            client_id=params.client_id,
            client_secret=params.secret_id,
            tenant=params.tenant,
            refresh_token=params.refresh_token,
            verify_ssl=params.verify_ssl,
        )
        return get_authenticated_session(session_parameters=session_parameters)


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
    session = CreateSession.create_session()

    retry_strategy = Retry(
        total=constants.HTTP_RETRY_TOTAL,
        status_forcelist=constants.HTTP_RETRY_STATUS_CODES,
        backoff_factor=constants.HTTP_RETRY_BACKOFF_FACTOR,
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
    session.verify = session_parameters.verify_ssl
    tokens = generate_tokens(
        session=session,
        session_parameters=session_parameters,
    )
    session.headers.update({"Authorization": f"Bearer {tokens.access_token}"})


def generate_tokens(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
) -> tuple[str, str]:
    """
    Generate a new access token and refresh token using the provided session and
    parameters.

    Args:
        session (requests.Session): The HTTP session object.
        session_parameters (SessionAuthenticationParameters): The session parameters
        containing client_id, client_secret, and refresh_token.

    Returns:
        tuple[str, str]: A tuple containing the access token and refresh token.
    """
    payload = copy.deepcopy(constants.TOKEN_PAYLOAD_FROM_SECRET)
    payload.update(
        {
            "client_id": session_parameters.client_id,
            "client_secret": session_parameters.client_secret,
            "refresh_token": session_parameters.refresh_token,
        }
    )

    url = api_utils.get_full_url(
        api_root=session_parameters.azure_ad_endpoint,
        url_id="access_token_url",
        tenant=session_parameters.tenant,
    )

    response = session.post(url, data=payload)
    api_utils.validate_response(response)

    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    return Tokens(access_token=access_token, refresh_token=refresh_token)


def get_refresh_token_from_code(
    session: requests.Session,
    session_parameters: SessionAuthenticationParameters,
    code: str,
    redirect_url: str,
) -> str:
    """Generate a refresh token from an Authorization Code as mentioned in documentation

    See: https://learn.microsoft.com/en-us/graph/auth-v2-user?tabs=http

    Args:
        session (requests.Session): The HTTP session object.
        session_parameters (SessionAuthenticationParameters): The session parameters
            containing client_id, client_secret, and tenant information.
        code (str): The authorization code obtained from the user's authentication flow.
        redirect_url (str): The redirect URI used during the authentication flow.

    Returns:
        str: The refresh token obtained from the token endpoint.  Returns None if
            there is an error.
    """
    session.verify = session_parameters.verify_ssl
    payload = copy.deepcopy(constants.TOKEN_PAYLOAD_FROM_SECRET)
    data = {
        "grant_type": "authorization_code",
        "client_id": session_parameters.client_id,
        "client_secret": session_parameters.client_secret,
        "redirect_uri": redirect_url,
        "code": code,
    }
    del payload["refresh_token"]
    payload.update(data)

    url = api_utils.get_full_url(
        api_root=session_parameters.azure_ad_endpoint,
        url_id="access_token_url",
        tenant=session_parameters.tenant,
    )

    response = session.post(url, data=payload)
    api_utils.validate_response(response)
    tokens = response.json()

    return tokens["refresh_token"]
