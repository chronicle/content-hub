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

from TIPCommon.base.utils import validate_manager

from ..core.GKEBaseAction import GKEBaseAction
from ..core.GKEConsts import INTEGRATION_IDENTIFIER, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME
from ..core.GKEServices import GKEBaseService


class Ping(GKEBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} "
            f"service with the provided connection parameters!"
        )
        self.error_output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} service!"
        )

    def _validate_params(self) -> None:
        pass

    def _extract_action_params(self) -> None:
        pass

    def _perform_action(self, manager: GKEBaseService | None = None, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)
        self.logger.info("Testing connectivity")
        manager.api_manager.test_connectivity()
        self.logger.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service!"
        )


def main() -> None:
    Ping(f"{INTEGRATION_IDENTIFIER} - {PING_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()
