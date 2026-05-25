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

from typing import Any

from ..core.base_action import AkeylessAction
from ..core.constants import PING_SCRIPT_NAME


class PingAction(AkeylessAction):
    """Action to test connectivity to Akeyless."""

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.error_output_message: str = "Failed to connect to the Akeyless server!"

    def _perform_action(self, _: Any = None) -> None:
        """Test connectivity to Akeyless.

        Raises:
            ConnectivityError: If the connectivity tests fail.
        """
        is_connected: bool = self.akeyless_client.test_connectivity()

        self.output_message = (
            "Successfully connected to the Akeyless server with the provided "
            "connection parameters!"
        )
        self.result_value = is_connected


def main() -> None:
    PingAction().run()


if __name__ == "__main__":
    main()
