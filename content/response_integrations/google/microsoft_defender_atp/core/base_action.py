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
from TIPCommon.extraction import extract_configuration_param
from . import constants
from .UtilsManager import DefenderATPManagerConfig, init_defender_atp_manager

if TYPE_CHECKING:
    from .MicrosoftDefenderATPManager import (
        MicrosoftDefenderATPManager,
        MicrosoftDefenderATPManagerV2,
    )


class BaseAction(Action, ABC):
    """
    Base action class for Microsoft Defender for Endpoint integration.
    """

    def _init_api_clients(
        self,
    ) -> MicrosoftDefenderATPManager | MicrosoftDefenderATPManagerV2:
        """
        Initialize the API client for Microsoft Defender for Endpoint.
        """
        login_api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Login API Root",
            default_value=constants.LOGIN_API_ROOT_DEFAULT,
            is_mandatory=True,
        )
        api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Api Root",
            is_mandatory=True,
        )
        client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Client ID",
            is_mandatory=True,
        )
        client_secret = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Client Secret",
            is_mandatory=True,
        )
        tenant_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Azure Active Directory ID",
            is_mandatory=True,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Verify SSL",
            input_type=bool,
            default_value=False,
        )
        graph_api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.PROVIDER_NAME,
            param_name="Graph API Root",
        )

        config = DefenderATPManagerConfig(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            resource=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
            chronicle_soar=self.soar_action,
            microsoft_graph_url=graph_api_root,
        )

        return init_defender_atp_manager(config=config)

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
