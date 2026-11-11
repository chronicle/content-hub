from __future__ import annotations
import dataclasses
import requests

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession

from proof_point_tap.core.constants import HEADERS
from proof_point_tap.core.datamodels import IntegrationParameters


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    username: str
    password: str
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
            username=params.username,
            password=params.password,
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
    session.auth = (session_parameters.username, session_parameters.password)
    session.headers = HEADERS
