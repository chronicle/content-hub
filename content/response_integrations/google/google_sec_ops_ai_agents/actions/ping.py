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

"""Ping action."""
from __future__ import annotations

from typing import TYPE_CHECKING
from google_sec_ops_ai_agents.core import consts
from google_sec_ops_ai_agents.core.base_action import BaseAction

if TYPE_CHECKING:
    from typing import NoReturn


SUCCESS_MESSAGE = (
    "Successfully connected to the Google Chronicle with the provided"
    " connection parameters!"
)
ERROR_MESSAGE = "Failed to connect to the Google Chronicle server!"
SCRIPT_NAME = "Ping"


class Ping(BaseAction):
    """Ping action."""

    def __init__(self) -> None:
        """Initialize a new Ping."""
        super().__init__(f"{consts.INTEGRATION_NAME} - {SCRIPT_NAME}")

    def _perform_action(self, _: None = None) -> None:
        self.api_client.test_connectivity()

    def _finalize_action_on_success(self) -> None:
        self.output_message = SUCCESS_MESSAGE

    def _finalize_action_on_failure(self, _: Exception) -> None:
        self.error_output_message = ERROR_MESSAGE


def main() -> NoReturn:
    """Execute the main function."""
    Ping().run()


if __name__ == "__main__":
    main()
