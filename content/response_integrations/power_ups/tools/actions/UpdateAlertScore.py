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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

ALERT_SCORE = "ALERT_SCORE"


@output_handler
def main():
    siemplify = SiemplifyAction()

    _input = siemplify.extract_action_param("Input")
    current_score = siemplify.get_alert_context_property(ALERT_SCORE)
    if current_score is not None:
        current_score = current_score.strip('"')
    else:
        current_score = 0

    new_score = str(int(current_score) + int(_input))
    siemplify.set_alert_context_property(ALERT_SCORE, new_score)

    result_value = new_score
    output_message = f"The Alert Score has been updated to: {new_score}"

    siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)


if __name__ == "__main__":
    main()
