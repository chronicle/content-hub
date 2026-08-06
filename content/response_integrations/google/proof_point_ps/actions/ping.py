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

from ..core.base_action import BaseProofPointPSAction
from ..core.constants import PING_ACTION_NAME
from ..core.exceptions import ProofPointPSError

from TIPCommon.base.action import ExecutionState

if TYPE_CHECKING:
    from typing import Never


class Ping(BaseProofPointPSAction):
    """Ping action to test connectivity."""

    def __init__(self) -> None:
        super().__init__(PING_ACTION_NAME)

    def _perform_action(self, _: Never) -> None:
        """Execute the connectivity test.

        Args:
            _: Never input.

        """
        try:
            self.api_client.test_connectivity()
            self.result_value = True
            self.output_message = (
                "Successfully connected to the Proofpoint Email Protection "
                "server with the provided connection parameters!"
            )
        except ProofPointPSError as e:
            error_msg = str(e)
            prefix = "Unable to search emails: "
            if error_msg.startswith(prefix):
                error_msg = error_msg[len(prefix):]

            self.result_value = False
            self.execution_state = ExecutionState.FAILED
            self.output_message = (
                "Failed to connect to the Proofpoint Email Protection server! "
                f"Error is {error_msg}"
            )


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
