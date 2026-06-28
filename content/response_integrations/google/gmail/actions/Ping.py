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

from gmail.core.GoogleGmailBaseAction import GoogleGmailBaseAction
from gmail.core.GoogleGmailConsts import (
    INTEGRATION_DISPLAY_NAME,
    PING_SCRIPT_NAME
)


SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} "
    f"service with the provided connection parameters!"
)
ERROR_MESSAGE = (
    f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} service!"
)


class Ping(GoogleGmailBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    async def _perform_action_async(self, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(self.api_client)
        self.logger.info("Testing connectivity")
        await self.api_client.test_connectivity()
        self.logger.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service!"
        )
        await self.api_client.close()


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
