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

"""ThreatConnect V3 core base action module."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from ..core.api.api_client import ApiParameters, ThreatConnectApiClient
from ..core.auth import AuthenticatedSession, SessionAuthenticationParameters, build_auth_params

if TYPE_CHECKING:
    import requests


class ThreatConnectAction(Action[ThreatConnectApiClient], ABC):
    """Base action class for ThreatConnect integration."""

    def _init_api_clients(self) -> ThreatConnectApiClient:
        """Initialize and return the ThreatConnect V3 API client using the standard TIPCommon interfaces.

        Returns:
            ThreatConnectApiClient: The configured API client.

        """
        auth_params = build_auth_params(self.soar_action)
        authenticator = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_access_id=auth_params.api_access_id,
            api_secret_key=auth_params.api_secret_key,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params = ApiParameters(
            api_root=auth_params.api_root,
            verify_ssl=auth_params.verify_ssl,
        )

        return ThreatConnectApiClient(
            authenticated_session=authenticated_session,  # type: ignore[arg-type]
            configuration=api_params,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        """Get the result value for the action."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        """Set the result value for the action."""
        self._result_value = value
