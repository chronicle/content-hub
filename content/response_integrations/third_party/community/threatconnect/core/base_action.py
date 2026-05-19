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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from ..core.api.api_client import ApiParameters, ThreatConnectApiClient
from ..core.api.auth import AuthenticatedSession
from ..core.constants import INTEGRATION_NAME


class ThreatConnectAction(Action, ABC):
    """Base action class for ThreatConnect integration."""

    def _init_api_clients(self) -> ThreatConnectApiClient:
        """Initialize and return the ThreatConnect V3 API client.

        Returns:
            ThreatConnectApiClient: The configured API client.

        """
        api_access_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Access ID",
            is_mandatory=True,
            input_type=str,
        )
        api_secret_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Secret Key",
            is_mandatory=True,
            input_type=str,
        )
        api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            input_type=str,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )

        session = AuthenticatedSession(api_access_id, api_secret_key)
        parameters = ApiParameters(api_root, verify_ssl)

        return ThreatConnectApiClient(session, parameters, self.logger)

    @property
    def result_value(self) -> bool:
        """Get the result value for the action."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        """Set the result value for the action."""
        self._result_value = value
