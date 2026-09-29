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

from google_cloud_api.core.GoogleCloudApiBaseAction import BaseAction
from google_cloud_api.core.GoogleCloudApiConstants import (
    PING_SCRIPT_NAME,
    INTEGRATION_IDENTIFIER,
)

SUCCESS_MESSAGE = "Successfully tested connectivity."
ERROR_MESSAGE = "Failed to test connectivity."


class Ping(BaseAction):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.test_url = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Test URL"
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity(self.params.test_url)
        self.json_results = {
            "endpoint": (
                self.api_client.placeholders.apply_placeholders(self.params.test_url)
            )
        }


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
