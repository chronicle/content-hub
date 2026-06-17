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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from .constants import INTEGRATION_NAME
from .CyberArkPamManager import CyberArkPamManager
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
            siemplify=self.soar_action,
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
            api_root = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Api Root",
                is_mandatory=True,
                print_value=True,
            )
            username = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Username",
                is_mandatory=True,
                print_value=True,
            )
            password = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Password",
                is_mandatory=True,
                remove_whitespaces=False,
            )
            verify_ssl = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Verify SSL",
                is_mandatory=False,
                input_type=bool,
                print_value=True,
            )
            ca_certificate = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="CA Certificate",
            )
            client_certificate = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Client Certificate",
            )
            client_certificate_passphrase = extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_NAME,
                param_name="Client Certificate Passphrase",
                remove_whitespaces=False,
            )
            self._integration_params = IntegrationParameters(
                api_root=api_root,
                username=username,
                password=password,
                verify_ssl=verify_ssl,
                ca_certificate=ca_certificate,
                client_certificate=client_certificate,
                client_certificate_passphrase=client_certificate_passphrase,
            )

        return self._integration_params
