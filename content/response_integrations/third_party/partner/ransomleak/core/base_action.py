# Copyright 2026 RansomLeak
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

"""Base class for the RansomLeak actions."""

from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from .constants import DEFAULT_API_ROOT, INTEGRATION_NAME
from .data_models import RansomLeakConfig
from .ransomleak_manager import RansomLeakManager


class BaseAction(Action, ABC):
    """Shared setup and teardown for the RansomLeak actions."""

    def __init__(self, script_name: str, action_name: str) -> None:
        """Create the action.

        Args:
            script_name: The SOAR script name, e.g. "RansomLeak - Ping".
            action_name: The display name used in error output messages.

        """
        super().__init__(script_name)
        self.error_output_message = f'Error executing action "{action_name}".'

    def _init_api_clients(self) -> RansomLeakManager:
        """Create the RansomLeak client from the integration configuration.

        Returns:
            A configured RansomLeakManager.

        """
        api_root: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            default_value=DEFAULT_API_ROOT,
            is_mandatory=True,
            print_value=True,
        )
        api_key: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Key",
            is_mandatory=True,
        )
        verify_ssl: bool = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
            print_value=True,
        )
        return RansomLeakManager(
            RansomLeakConfig(
                api_root=api_root,
                api_key=api_key,
                verify_ssl=verify_ssl,
            ),
        )

    def _finalize(self) -> None:
        """Close every HTTP session the client opened."""
        if isinstance(self.api_client, RansomLeakManager):
            self.api_client.close()
