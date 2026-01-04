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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import parse_raw_message

# CONSTS
OPEN_PH_PARENTHASIS = "{"
CLOSE_PH_PARENTHASIS = "}"
PIPE = "|"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = "No insight created"
    result_value = False

    raw_message = siemplify.parameters.get("Message")

    try:
        successful_entities = []
        for entity in siemplify.target_entities:
            message = parse_raw_message(entity.additional_properties, raw_message)
            if message:  # and found_anything:
                output_message = message
                siemplify.add_entity_insight(
                    entity,
                    message,
                    triggered_by=siemplify.parameters.get("Triggered By", "Siemplify"),
                )
                successful_entities.append(entity)

        if successful_entities:
            result_value = True
            output_message = "Insights added for:\n{}".format(
                "\n".join([x.identifier for x in successful_entities]),
            )

        siemplify.end(output_message, result_value, EXECUTION_STATE_COMPLETED)

    except Exception as e:
        raise
        siemplify.end(f"Errors found: {e}", "Failed", EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
