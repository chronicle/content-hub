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

from ..core.api.api_client import (
    ApiParameters,
    SentinelOneSingularityOperationsCenterApiClient,
)
from ..core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
)

if TYPE_CHECKING:
    import requests


class SentinelOneSingularityOperationsCenterAction(Action, ABC):
    """Base action class."""

    api_client: SentinelOneSingularityOperationsCenterApiClient

    def _init_api_clients(self) -> SentinelOneSingularityOperationsCenterApiClient:
        """Prepare API client.

        Returns:
            SentinelOneSingularityOperationsCenterApiClient: SentinelOne API Client.

        """
        auth_params = build_auth_params(self.soar_action)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_root=auth_params.api_root,
            api_token=auth_params.api_token,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        return SentinelOneSingularityOperationsCenterApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        """The result value of the action.

        Returns:
            bool: True if the action succeeded, False otherwise.

        """
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
