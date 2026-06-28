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

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob

from TIPCommon.base.interfaces import Authable
from TIPCommon.base.utils import CreateSession
from TIPCommon.extraction import extract_script_param

from proofpoint_cloud_threat_response.core.api_utils import validate_response
from proofpoint_cloud_threat_response.core.constants import (
    DEFAULT_API_ROOT,
    DEFAULT_VERIFY_SSL,
    INTEGRATION_IDENTIFIER,
)
from proofpoint_cloud_threat_response.core.data_models import IntegrationParameters
from proofpoint_cloud_threat_response.core.exceptions import ProofpointCTRError

if TYPE_CHECKING:
    from requests import Session

    from TIPCommon.types import ChronicleSOAR


@dataclasses.dataclass(slots=True)
class SessionAuthenticationParameters:
    client_id: str
    client_secret: str
    auth_url: str
    verify_ssl: bool


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Extract auth params for Auth manager

    Args:
         soar_sdk_object: ChronicleSOAR SDK object

    Returns:
        IntegrationParameters: IntegrationParameters object.

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
        raise ProofpointCTRError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    return IntegrationParameters(
        api_root=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="API Root",
            default_value=DEFAULT_API_ROOT,
            is_mandatory=True,
            print_value=True,
        ),
        client_id=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Client ID",
            is_mandatory=True,
            print_value=True,
        ),
        client_secret=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Client Secret",
            is_mandatory=True,
        ),
        verify_ssl=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Verify SSL",
            default_value=DEFAULT_VERIFY_SSL,
            input_type=bool,
            is_mandatory=True,
            print_value=True,
        ),
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
    payload = {
        "client_id": session_parameters.client_id,
        "client_secret": session_parameters.client_secret,
        "grant_type": "client_credentials",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = session.post(session_parameters.auth_url, data=payload, headers=headers)
    validate_response(response)

    bearer_token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {bearer_token}"})
