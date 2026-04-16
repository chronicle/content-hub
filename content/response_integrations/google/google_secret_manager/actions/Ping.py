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

from ..core.GoogleSecretManagerBaseAction import GoogleSecretManagerAction
from ..core.GoogleSecretManagerConstants import PING_SCRIPT_NAME


class PingAction(GoogleSecretManagerAction):
    """Action to test connectivity to Google Secret Manager."""

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)

    def _perform_action(self, _=None) -> None:
        """Test connectivity to Google Secret Manager."""
        is_connected = self.secret_manager_client.test_connectivity()

        self.output_message = (
            "Successfully connected to Google Secret Manager."
        )
        self.result_value = is_connected


def main() -> None:
    PingAction().run()


if __name__ == "__main__":
    main()
