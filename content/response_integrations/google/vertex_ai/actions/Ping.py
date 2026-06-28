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
from vertex_ai.core.VertexAIBaseAction import BaseAction
from vertex_ai.core.VertexAIConstants import PING_SCRIPT_NAME

SUCCESS_MESSAGE = (
    "Successfully connected to Vertex AI with the provided connection parameters!"
)
ERROR_MESSAGE = "Failed to connect to Vertex AI!"


class Ping(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        publisher_name = self.params.default_publisher_name
        self.api_client.test_connectivity(
            model_id=self.params.default_model, publisher_name=publisher_name,
        )


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
