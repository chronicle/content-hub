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

from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.UtilsManager import get_integration_parameters
from ..core.AuthManager import AuthenticateSession
from ..core.ZohoDeskApiManager import ZohoDeskApiClient
from ..core.datamodels import IntegrationParameters


def create_api_client(soar_action: SiemplifyAction) -> ZohoDeskApiClient:
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    authenticator.authenticate_session(params)
    return ZohoDeskApiClient(authenticator.session, params)
