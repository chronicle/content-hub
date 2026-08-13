# Copyright 2025 Google LLC
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

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction


def main() -> None:
    """Main execution logic for the Buffer action."""
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED

    result_value = siemplify.parameters.get("ResultValue")
    output_message = "Input values 'transferred' to the output."
    
    if siemplify.parameters.get("JSON"):
        try:
            data = json.loads(siemplify.parameters.get("JSON"))
            siemplify.result.add_result_json(data)
        except Exception as e:
            output_message = f"Failed to load JSON with error: {e}"
            status = EXECUTION_STATE_FAILED
            result_value = "failed"

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
