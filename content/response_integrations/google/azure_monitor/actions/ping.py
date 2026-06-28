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

from typing import TYPE_CHECKING

from azure_monitor.core.base_action import BaseAction
from azure_monitor.core.constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the Azure Monitor server with the provided "
    "connection parameters!"
)
ERROR_MESSAGE: str = "Failed to connect to the Azure Monitor server!"


class Ping(BaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
