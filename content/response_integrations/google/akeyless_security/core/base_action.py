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

"""Base action class for Akeyless Security actions."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from .authentication import build_auth_params
from .manager import AkeylessSecurityClient

if TYPE_CHECKING:
    from .datamodels import AkeylessSecurityClientConfig


class AkeylessSecurityAction(Action, ABC):
    """Base action class for Akeyless Security actions."""

    def __init__(self, script_name: str) -> None:
        """Initialize the base action."""
        super().__init__(script_name)
        self.akeyless_security_client: AkeylessSecurityClient | None = None
        self.error_output_message: str = ""

    def _init_api_clients(self) -> AkeylessSecurityClient:
        """Extract configuration and initialize the AkeylessSecurity API client.

        Returns:
            The initialized AkeylessSecurity API client.

        """
        config: AkeylessSecurityClientConfig = build_auth_params(self.soar_action)
        self.akeyless_security_client = AkeylessSecurityClient(config)

        return self.akeyless_security_client
