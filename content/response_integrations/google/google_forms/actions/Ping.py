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

from typing import NoReturn

from TIPCommon.base.action import Action
from ..core import constants
from ..core.action_init import create_api_client
from ..core.GoogleFormsManager import GoogleFormsManager


SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {constants.INTEGRATION_NAME} server with "
    "the provided connection parameters!"
)
ERROR_MESSAGE: str = f"Failed to connect to the {constants.INTEGRATION_NAME} server!"


class Ping(Action):
    def __init__(self) -> None:
        super().__init__(constants.PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _init_api_clients(self) -> GoogleFormsManager:
        return create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self._api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
