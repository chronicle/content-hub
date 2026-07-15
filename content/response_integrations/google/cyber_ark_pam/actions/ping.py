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

"""Ping action for CyberArk PAM integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import CyberArkPamAction
from ..core.constants import INTEGRATION_NAME

if TYPE_CHECKING:
    from TIPCommon.types import Entity

SCRIPT_NAME = "Ping"


class Ping(CyberArkPamAction):
    """Ping action class."""

    def __init__(self) -> None:
        """Initialize the Ping action."""
        super().__init__(f"{INTEGRATION_NAME} - {SCRIPT_NAME}")

    def _extract_action_parameters(self) -> None:
        """Extract action parameters from SOAR."""

    def _perform_action(self, _: Entity | None = None) -> None:
        """Perform the action logic."""
        try:
            self.logger.info(f"Connecting to {INTEGRATION_NAME}.")
            self.api_client.test_connectivity()
            self.output_message = f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters!"
            self.result_value = True
        except Exception as e:
            log_message = (
                f"Failed to connect to the {INTEGRATION_NAME} server! Error is {e}"
            )
            self.logger.exception(log_message)
            self.output_message = log_message
            self.result_value = False
            raise


def main() -> None:
    """Run the Ping action."""
    Ping().run()


if __name__ == "__main__":
    main()
