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
from .exceptions import SignalSciencesIntegrationError


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    email: str
    api_token: str
    verify_ssl: bool


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    sdk_class = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (SiemplifyConnectorExecution.__name__, SiemplifyJob.__name__):
        input_dictionary = soar_sdk_object.parameters
    else:
        msg = f"Provided SOAR instance is not supported! type: {sdk_class}."
        raise SignalSciencesIntegrationError(msg)

    api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        is_mandatory=True,
    )
    email = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Email",
        is_mandatory=True,
    )
    api_token = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Token",
        is_mandatory=True,
    )
    corp_name = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Corporation Name",
        is_mandatory=True,
    )
    verify_ssl = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        default_value=DEFAULT_VERIFY_SSL,
        input_type=bool,
        is_mandatory=True,
    )

    return IntegrationParameters(
        api_root=api_root,
        email=email,
        api_token=api_token,
        corp_name=corp_name,
        verify_ssl=verify_ssl
    )


class AuthenticatedSession(Authable):
    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        self.session = get_authenticated_session(params)


def get_authenticated_session(params: SessionAuthenticationParameters) -> Session:
    session: Session = CreateSession.create_session()
    session.verify = params.verify_ssl
    session.headers.update({
        "x-api-user": params.email,
        "x-api-token": params.api_token,
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    return session
