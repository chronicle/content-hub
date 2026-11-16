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

from ..core.SysdigSecureBaseAction import BaseAction
from ..core.SysdigSecureConstants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the "
    f"provided connection parameters!"
)

ERROR_MESSAGE = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server!"


class Ping(BaseAction):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.json_results = {}

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
