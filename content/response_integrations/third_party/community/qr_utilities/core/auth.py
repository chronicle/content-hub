from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from requests import Session
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_configuration_param

from .constants import INTEGRATION_IDENTIFIER

if TYPE_CHECKING:
    from SiemplifyAction import SiemplifyAction


@dataclass
class SessionAuthenticationParameters:
    api_root: str
    verify_ssl: bool


def build_auth_params(soar_action: SiemplifyAction) -> SessionAuthenticationParameters:
    return SessionAuthenticationParameters(
        api_root=extract_configuration_param(
            siemplify=soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        ),
        verify_ssl=extract_configuration_param(
            siemplify=soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            is_mandatory=True,
            print_value=True,
            input_type=bool,
        ),
    )


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> Session:
    """Get authenticated session with provided configuration parameters.

    Args:
        session_parameters (SessionAuthenticationParameters): Session parameters.

    Returns:
        Session: Authenticated session object.
    """
    session: Session = CreateSession.create_session()
    session.verify = session_parameters.verify_ssl

    return session
