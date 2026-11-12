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

from collections import namedtuple
import copy
import dataclasses
from typing import TYPE_CHECKING, Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param
from TIPCommon.transformation import string_to_multi_value
from . import api_utils
from .constants import (
    DEFAULT_GRAPH_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    DEFAULT_SCOPE,
    DEFAULT_VERIFY_SSL,
    GRANT_TYPE_CLIENT_CREDENTIALS,
    GRANT_TYPE_REFRESH_TOKEN,
    INTEGRATION_IDENTIFIER,
    PARAM_CLIENT_ID,
    PARAM_CLIENT_SECRET,
    PARAM_GRAPH_API_ROOT,
    PARAM_LOGIN_API_ROOT,
    PARAM_REDIRECT_URL,
    PARAM_REFRESH_TOKEN,
    PARAM_SCOPE,
    PARAM_TENANT_ID,
    PARAM_VERIFY_SSL,
    TOKEN_PAYLOAD_FROM_SECRET,
)
from .data_models import IntegrationParameters
from .exceptions import AzureApiError

if TYPE_CHECKING:
    from requests import Session

    from TIPCommon.types import ChronicleSOAR, SingleJson


Tokens = namedtuple("Tokens", ["access_token", "refresh_token"])


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    login_api_root: str
    api_root: str
    tenant_id: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    scopes: list[str]
    refresh_token: str
    redirect_url: str


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """
    Builds integration parameters from the SOAR SDK object.

    Args:
        soar_sdk_object (ChronicleSOAR): The SOAR SDK object
            (SiemplifyAction, SiemplifyConnectorExecution, or SiemplifyJob).

    Returns:
        IntegrationParameters: An object containing the extracted integration
            parameters.

    Raises:
        AzureApiError: If the provided SOAR instance is not supported.
    """
    sdk_class: str = type(soar_sdk_object).__name__
    input_dictionary: dict[str, Any]

    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    ):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise AzureApiError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    return IntegrationParameters(
        login_api_root=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_LOGIN_API_ROOT,
            default_value=DEFAULT_LOGIN_API_ROOT,
            is_mandatory=True,
            print_value=True,
        ),
        api_root=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_GRAPH_API_ROOT,
            default_value=DEFAULT_GRAPH_API_ROOT,
            is_mandatory=True,
            print_value=True,
        ),
        tenant_id=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_TENANT_ID,
            is_mandatory=True,
            print_value=True,
        ),
        client_id=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_CLIENT_ID,
            is_mandatory=True,
            print_value=True,
        ),
        client_secret=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_CLIENT_SECRET,
            is_mandatory=True,
        ),
        verify_ssl=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_VERIFY_SSL,
            default_value=DEFAULT_VERIFY_SSL,
            input_type=bool,
            is_mandatory=True,
            print_value=True,
        ),
        scopes=string_to_multi_value(
            extract_script_param(
                soar_sdk_object,
                input_dictionary=input_dictionary,
                param_name=PARAM_SCOPE,
                is_mandatory=False,
                default_value=DEFAULT_SCOPE,
                print_value=True,
            )
        ),
        refresh_token=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_REFRESH_TOKEN,
            is_mandatory=False,
        ),
        redirect_url=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name=PARAM_REDIRECT_URL,
            is_mandatory=False,
            print_value=True,
        ),
    )


class AuthenticatedSession(Authable):
    session: Session

    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        self.session = get_authenticated_session(params)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> Session:
    """Create and authenticate a requests session.

    Args:
        session_parameters (SessionAuthenticationParameters): Parameters for session
        authentication.

    Returns:
        Session: Authenticated session.
    """
    session: Session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)
    return session


def _authenticate_session(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    session.verify = session_parameters.verify_ssl
    tokens: Tokens = generate_tokens(session, session_parameters)
    session.headers.update({"Authorization": f"Bearer {tokens.access_token}"})


def generate_tokens(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> Tokens:
    """Generate access token using client credentials or refresh token.

    Args:
        session (Session): Requests session.
        session_parameters (SessionAuthenticationParameters): Parameters for session
        authentication.
    Returns:
        Tokens: Named tuple containing access and refresh tokens.
    """
    payload: SingleJson = copy.deepcopy(TOKEN_PAYLOAD_FROM_SECRET)
    grant_type: str = GRANT_TYPE_REFRESH_TOKEN

    if session_parameters.refresh_token is None:
        grant_type = GRANT_TYPE_CLIENT_CREDENTIALS

    payload.update(
        {
            "client_id": session_parameters.client_id,
            "client_secret": session_parameters.client_secret,
            "refresh_token": session_parameters.refresh_token,
            "grant_type": grant_type,
            "scope": " ".join(session_parameters.scopes),
        },
    )
    token_url: str = api_utils.get_full_url(
        api_root=session_parameters.login_api_root,
        endpoint_id="bearer_token_url",
        tenant_id=session_parameters.tenant_id,
    )

    response = session.post(token_url, data=payload)
    api_utils.validate_response(response)

    token_info: SingleJson = response.json()
    access_token = token_info.get("access_token")
    refresh_token = token_info.get("refresh_token")

    return Tokens(access_token=access_token, refresh_token=refresh_token)
