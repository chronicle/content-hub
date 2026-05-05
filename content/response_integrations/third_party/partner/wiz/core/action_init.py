# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from . import api_client
from .auth_manager import AuthenticateSession, SessionAuthenticationParameters
from .datamodels import IntegrationParameters
from .utils import get_integration_parameters

if TYPE_CHECKING:
    import requests

    from TIPCommon.types import ChronicleSOAR


def create_api_client(soar_action: ChronicleSOAR) -> api_client.WizApiClient:
    """Create Wiz WizApiClient object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        api_client.WizApiClient: WizApiClient object.
    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession = AuthenticateSession()
    auth_params_for_session = SessionAuthenticationParameters(
        api_root=params.api_root,
        client_id=params.client_id,
        client_secret=params.client_secret,
        verify_ssl=params.verify_ssl,
    )
    authenticator.authenticate_session(auth_params_for_session)
    authenticated_session: requests.Session = authenticator.session

    api_params: api_client.ApiParameters = api_client.ApiParameters(
        api_root=params.api_root,
    )

    return api_client.WizApiClient(
        authenticated_session=authenticated_session,
        configuration=api_params,
        logger=params.siemplify_logger,
    )
