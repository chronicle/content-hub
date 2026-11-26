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

from __future__ import annotations

from typing import NoReturn

from ..core.base_action import BaseAction
from ..core.constants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME

SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the provided connection parameters!"
)
ERROR_MESSAGE: str = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server!"


class PingAction(BaseAction):
    """Verify the API Root and API Key with an authenticated request."""

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME, "Ping")
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _: object = None) -> None:
        self.api_client.test_connectivity()
        self.output_message = SUCCESS_MESSAGE
        self.result_value = True


def main() -> NoReturn:
    PingAction().run()


if __name__ == "__main__":
    main()
