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

from ..core.base_action import ZscalerBaseAction
from ..core.constants import PING_SCRIPT_NAME
from ..core.exceptions import ZscalerManagerError


class PingAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = "Connection Established"
        self.result_value: bool = False

    def _perform_action(self, _=None) -> None:
        """Perform the ping action."""
        try:
            self.api_client.test_connectivity()
            self.result_value = True
        except Exception as error:
            raise ZscalerManagerError(
                f"Failed to connect to the Zscaler server! {error}"
            ) from error


def main() -> None:
    PingAction().run()


if __name__ == "__main__":
    main()
