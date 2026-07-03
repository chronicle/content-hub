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
from ..core import exceptions
from ..core.NmapManager import NmapManager


class Ping(Action):
    def __init__(self) -> None:
        super().__init__(constants.PING_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = "Failed to connect to the Nmap server!"

    def _init_api_clients(self) -> NmapManager:
        return NmapManager(self.soar_action)

    def _perform_action(self, _) -> None:
        result = self.api_client.test_connectivity()

        if result.returncode != constants.SUCCESS_RETURN_CODE:
            raise exceptions.NmapManagerError(result.stderr)

        self.output_message = (
            "Successfully connected to the Nmap "
            "server with the provided connection parameters!"
        )


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
