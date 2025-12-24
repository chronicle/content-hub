from __future__ import annotations

import dataclasses

from requests import Session
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param
from TIPCommon.types import ChronicleSOAR

from .constants import DEFAULT_API_ROOT, DEFAULT_VERIFY_SSL, INTEGRATION_IDENTIFIER
from .data_models import IntegrationParameters
from .exceptions import SampleIntegrationError


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    api_root: str
    password: str
    verify_ssl: bool


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract auth params for Auth manager

    Args:
         soar_sdk_object: ChronicleSOAR SDK object

    Returns:
        SessionAuthenticationParameters: SessionAuthenticationParameters object.

    """
    sdk_class = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    ):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise SampleIntegrationError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    password = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Password Field",
    )
    verify_ssl = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        default_value=DEFAULT_VERIFY_SSL,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    return IntegrationParameters(
        api_root=api_root,
        password=password,
        verify_ssl=verify_ssl,
    )


class AuthenticatedSession(Authable):
    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        self.session = get_authenticated_session(session_parameters=params)


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
    _authenticate_session(session, session_parameters=session_parameters)

    return session


def _authenticate_session(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    session.verify: bool = session_parameters.verify_ssl
    password: str = (
        session_parameters.password.encode("utf-8").decode("iso-8859-1")
        if session_parameters.password
        else ""
    )
    session.headers.update({"dummy-password-header": f"{password}"})
