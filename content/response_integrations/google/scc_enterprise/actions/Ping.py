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

from TIPCommon.base.action import Action
from ..core import SCCEnterpriseConsts


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully tested {SCCEnterpriseConsts.INTEGRATION_NAME}."
        )
        self.error_output_message = (
            f"Failed to test {SCCEnterpriseConsts.INTEGRATION_NAME}"
        )

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        pass


def main() -> None:
    Ping(SCCEnterpriseConsts.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
