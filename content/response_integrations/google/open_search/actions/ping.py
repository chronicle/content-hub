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
from ..core import constants
from ..core.base_action import BaseAction

if TYPE_CHECKING:
    from typing import Never, NoReturn


class Ping(BaseAction):
    def __init__(self):
        super().__init__(constants.PING_SCRIPT_NAME)

    def _perform_action(self, _: Never) -> None:
        self.api_client.test_connectivity()
        self.output_message: str = "Successfully connected to the OpenSearch server."
        self.result_value: bool = True


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
