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

from TIPCommon.extraction import extract_configuration_param

from ..core.base_action import BaseAction
from ..core.constants import (
    INTEGRATION_IDENTIFIER,
    PING_SCRIPT_NAME,
    PING_SUCCESS_MESSAGE,
)


class PingAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.identifier = INTEGRATION_IDENTIFIER
        self.output_message = PING_SUCCESS_MESSAGE
        self.result_value = True

    def _extract_action_parameters(self) -> None:
        self.params.test_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Test URL",
        )

    def _validate_params(self) -> None: ...

    def _perform_action(self, _: None) -> None:
        self.api_client.test_connectivity(self.params.test_url)
        self.json_results = {
            "endpoint": (
                self.api_client.placeholders.apply_placeholders(self.params.test_url)
            )
        }


def main() -> None:
    action = PingAction()
    action.run()


if __name__ == "__main__":
    main()
