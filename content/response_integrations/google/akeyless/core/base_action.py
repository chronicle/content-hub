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

from .authentication import IntegrationParameters, build_auth_params
from .manager import AkeylessClient, AkeylessClientConfig


class AkeylessAction(Action, ABC):
    """Base action class for Akeyless actions."""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.akeyless_client: AkeylessClient | None = None
        self.error_output_message: str = ""

    def _init_api_clients(self) -> AkeylessClient:
        """Extract config and initialize the API client.

        Returns:
            AkeylessClient: The initialized client.

        """
        auth_params: IntegrationParameters = build_auth_params(self.soar_action)

        config = AkeylessClientConfig(
            access_id=auth_params.access_id,
            access_key=auth_params.access_key,
            access_type=auth_params.access_type,
            api_gateway_url=auth_params.api_gateway_url,
            verify_ssl=auth_params.verify_ssl,
        )

        self.akeyless_client = AkeylessClient(
            config,
            logger=self.logger,
        )

        return self.akeyless_client
