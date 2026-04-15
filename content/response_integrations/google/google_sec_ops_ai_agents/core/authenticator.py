from __future__ import annotations

from typing import TYPE_CHECKING
from . import consts
from . import exceptions
import requests
from ..core.data_models import SessionAuthenticationParameters
from google.auth.transport.requests import AuthorizedSession, Request
from TIPCommon.base.interfaces import Authable
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials
import TIPCommon.base.utils

if TYPE_CHECKING:
    import google.auth.credentials


class Authenticator(Authable):
    """Authenticator for Chronicle SOAR."""

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        """Authenticate a session.

        Args:
            params: The session authentication parameters.
        """
        credentials = _create_auth_credentials(params)
        self.session = AuthorizedSession(
            credentials,
            auth_request=_create_auth_request(verify_ssl=params.verify_ssl),
        )
        self.session.verify = params.verify_ssl


def _create_auth_credentials(
    auth_params: SessionAuthenticationParameters,
) -> google.auth.credentials.Credentials:
    """Create authentication credentials.

    Args:
        auth_params: The authentication parameters.

    Returns:
        The authentication credentials.
    """
    if "backstory" in auth_params.api_root:
        raise exceptions.ChronicleInvestigationManagerError(exceptions.INVALID_API_ROOT_ERROR)

    return get_secops_siem_tenant_credentials(
        auth_params.chronicle_soar,
        target_scopes=consts.OAUTH_SCOPES,
        fallback_to_env_email=True,
    )


def _create_auth_request(*, verify_ssl: bool) -> Request:
    """Create an authentication request.

    Args:
        verify_ssl: Whether to verify SSL.

    Returns:
        The authentication request.
    """
    auth_request_session = TIPCommon.base.utils.CreateSession.create_session()
    auth_request_session.verify = verify_ssl
    retry_adapter = requests.adapters.HTTPAdapter(max_retries=3)
    auth_request_session.mount("https://", retry_adapter)
    return Request(auth_request_session)
