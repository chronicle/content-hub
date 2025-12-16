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

import base64
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        "output message :"
    )
    result_value = True
    base64_input = siemplify.parameters.get("Base64 Input")
    encoding = siemplify.extract_action_param(
        param_name="Encoding",
        is_mandatory=True,
        print_value=True,
        default_value="ascii",
    )

    try:
        decoded_content = str(base64.b64decode(base64_input), encoding)
        result = {"decoded_content": decoded_content}
        siemplify.result.add_result_json(json.dumps(result))
        output_message = (
            f"Content was succesfully decoded from base 64 to string with encoding {encoding}"
        )

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"Error: {e}"
        result_value = False

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
