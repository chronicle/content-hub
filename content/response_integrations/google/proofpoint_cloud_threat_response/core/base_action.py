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

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from proofpoint_cloud_threat_response.core.api_client import ApiParameters, ProofpointCloudThreatResponseApiClient
from proofpoint_cloud_threat_response.core.auth import (
    AuthenticatedSession,
    build_auth_params,
    SessionAuthenticationParameters,
)
from proofpoint_cloud_threat_response.core.constants import AUTH_URL

if TYPE_CHECKING:
    import requests


class ProofpointCloudThreatResponseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ProofpointCloudThreatResponseApiClient:
        """Prepare API client"""
        auth_params = build_auth_params(self.soar_action)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            client_id=auth_params.client_id,
            client_secret=auth_params.client_secret,
            auth_url=AUTH_URL,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: AuthenticatedSession = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        return ProofpointCloudThreatResponseApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
