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
from TIPCommon.types import ChronicleSOAR

from extrahop.core.AuthenticationManager import AuthenticateSession
from extrahop.core.UtilsManager import get_integration_parameters
from extrahop.core import ExtrahopManager as api_manager
from extrahop.core.datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ExtrahopManager:
    """Create Extrahop ApiManager client object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        api_manager.ApiManager: ApiManager object.
    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    session = authenticator.authenticate_session(params)
    api_params = api_manager.ApiParameters(
        api_root=params.api_root,
        client_id=params.client_id,
        client_secret=params.client_secret,
    )

    return api_manager.ExtrahopManager(
        session=session,
        api_parameters=api_params,
    )
