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
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param
from ..core import api_utils
from ..core.constants import (
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    DEFAULT_VERIFY_SSL,
    INTEGRATION_IDENTIFIER,
    TOKEN_PAYLOAD_FROM_SECRET,
)
from ..core.data_models import IntegrationParameters
from ..core.exceptions import AzureMonitorError

if TYPE_CHECKING:
    from requests import Session

    from TIPCommon.types import ChronicleSOAR


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    login_api_root: str
    api_root: str
    tenant_id: str
    client_id: str
    client_secret: str
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
        raise AzureMonitorError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    login_api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    api_root = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        is_mandatory=True,
        print_value=True,
    )
    tenant_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Tenant ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Client Secret",
        is_mandatory=True,
    )
    workspace_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Workspace ID",
        is_mandatory=True,
        print_value=True,
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
        login_api_root=login_api_root,
        api_root=api_root,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
        workspace_id=workspace_id,
        verify_ssl=verify_ssl,
    )


class AuthenticatedSession(Authable):
    def authenticate_session(self, params: SessionAuthenticationParameters) -> None:
        self.session = get_authenticated_session(params)


def get_authenticated_session(
    session_parameters: SessionAuthenticationParameters,
) -> Session:
    """Returns a requests Session object authenticated with a Bearer token.
    Args:
        session_parameters (SessionAuthenticationParameters): The authentication
        parameters.

    Returns:
        Session: The authenticated requests Session object.
    """
    session: Session = CreateSession.create_session()
    _authenticate_session(session, session_parameters=session_parameters)
    return session


def _authenticate_session(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> None:
    """Perform OAuth2 Client Credentials authentication to obtain and attach an access
    token.
    Args:
        session (Session): The requests Session object to authenticate.
        session_parameters (SessionAuthenticationParameters): The authentication
        parameters.
    """
    session.verify = session_parameters.verify_ssl
    access_token = generate_tokens(session, session_parameters)

    session.headers.update({"Authorization": f"Bearer {access_token}"})


def generate_tokens(
    session: Session,
    session_parameters: SessionAuthenticationParameters,
) -> str:
    """Generate access token using client credentials flow.

    Args:
        session (Session): The requests session to use for the token request.
        session_parameters (SessionAuthenticationParameters): The authentication
        parameters.

    Returns:
        str: The access token.
    """
    payload = copy.deepcopy(TOKEN_PAYLOAD_FROM_SECRET)
    payload.update(
        {
            "client_id": session_parameters.client_id,
            "client_secret": session_parameters.client_secret,
            "resource": session_parameters.api_root,
        }
    )
    token_url = api_utils.get_full_url(
        api_root=session_parameters.login_api_root,
        endpoint_id="bearer_token_url",
        tenant_id=session_parameters.tenant_id,
    )

    response = session.post(token_url, data=payload)
    api_utils.validate_response(response)

    token_info = response.json()
    access_token = token_info.get("access_token")

    return access_token
