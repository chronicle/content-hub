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

from . import consts
from .api_manager import CloudIdentityApiParameters, GoogleCloudIdentityApiManager
from .authentication_manager import AuthenticatedSession, SessionAuthenticationParameters
from .utils import get_integration_parameters

if TYPE_CHECKING:
    from google.auth.transport.requests import AuthorizedSession

    from .datamodels import IntegrationParameters


class CloudIdentityAction(Action, ABC):
    """Base action class for Cloud Identity integration."""

    def _init_api_clients(self) -> None:
        """Initialize API clients placeholder."""
        self.logger.debug("Initializing API clients placeholder...")

    def _get_integration_params(self) -> IntegrationParameters:
        """Get integration parameters from SOAR configuration.

        Returns:
            IntegrationParameters with configuration values.

        """
        if not hasattr(self, "_integration_params"):
            self._integration_params = get_integration_parameters(self.soar_action)
        return self._integration_params

    def _get_authenticated_session(self) -> AuthorizedSession:
        """Get an authenticated session for API requests.

        Returns:
            AuthorizedSession object.

        """
        params = self._get_integration_params()
        session_params = SessionAuthenticationParameters(
            service_account_json=params.service_account_json,
            workload_identity_email=params.workload_identity_email,
            delegated_email=params.delegated_email,
            verify_ssl=params.verify_ssl,
        )
        authenticator = AuthenticatedSession()
        authenticator.authenticate_session(session_params)
        return authenticator.session

    def _get_api_manager(self) -> GoogleCloudIdentityApiManager:
        """Get a Cloud Identity API manager.

        Returns:
            Configured GoogleCloudIdentityApiManager instance.

        """
        session = self._get_authenticated_session()
        return GoogleCloudIdentityApiManager(
            authenticated_session=session,
            configuration=CloudIdentityApiParameters(api_root=consts.DEFAULT_API_ROOT),
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        """Get the result value."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        """Set the result value."""
        self._result_value = value
