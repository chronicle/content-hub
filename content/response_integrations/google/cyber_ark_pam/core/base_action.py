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

"""Base action module for CyberArk PAM integration."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from .cyber_ark_pam_manager import CyberArkPamManager
from .utils import extract_integration_parameters

if TYPE_CHECKING:
    from .datamodels import IntegrationParameters


class CyberArkPamAction(Action, ABC):
    """Base action class for CyberArk PAM integration."""

    api_client: CyberArkPamManager

    def _init_api_clients(self) -> CyberArkPamManager:
        """Initialize CyberArkPamManager.

        Returns:
            Configured CyberArkPamManager instance.

        """
        params = self._get_integration_params()
        return CyberArkPamManager(
            api_root=params.api_root,
            username=params.username,
            password=params.password,
            logger=self.logger,
            verify_ssl=params.verify_ssl,
            ca_certificate=params.ca_certificate,
            client_certificate=params.client_certificate,
            client_certificate_passphrase=params.client_certificate_passphrase,
        )

    def _get_integration_params(self) -> IntegrationParameters:
        """Get integration parameters from SOAR configuration.

        Returns:
            IntegrationParameters with configuration values.

        """
        if not hasattr(self, "_integration_params"):
            self._integration_params = extract_integration_parameters(self.soar_action)

        return self._integration_params
