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

"""Base action for Google Chronicle."""
from __future__ import annotations

from abc import ABC

from google_sec_ops_ai_agents.core.api_client import ChronicleInvestigationApiClient
from google_sec_ops_ai_agents.core.authenticator import Authenticator
from google_sec_ops_ai_agents.core.data_models import ApiParameters, SessionAuthenticationParameters
from TIPCommon.base.action import Action
from google_sec_ops_ai_agents.core.utils import build_integration_params


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ChronicleInvestigationApiClient:
        """Prepare API client."""
        integration_params = build_integration_params(self.soar_action)
        auth_params = SessionAuthenticationParameters.from_integration_params(
            chronicle_soar=self.soar_action,
            integration_params=integration_params,
        )
        authenticator = Authenticator()
        authenticator.authenticate_session(auth_params)
        api_params = ApiParameters.from_integration_params(integration_params)

        return ChronicleInvestigationApiClient(
            api_params=api_params,
            authenticated_session=authenticator.session,
            logger=self.logger,
        )
