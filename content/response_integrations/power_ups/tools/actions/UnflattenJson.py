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
import re
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

SingleJson = dict[str, Any]
ListJson = list[SingleJson]
Json = SingleJson | ListJson

ACTION_NAME = "Unflatten JSON"


def unflatten_json(json_: Json, delimiter: str | None = None) -> Json:
    if isinstance(json_, list):
        return unflatten_list(json_, delimiter)

    return unflatten_dict(json_, delimiter)


def unflatten_list(json_: Json, delimiter: str | None = None) -> ListJson:
    results = []
    for item in json_:
        if isinstance(item, list):
            results.append(unflatten_list(item, delimiter))

        else:
            results.append(unflatten_dict(item))

    return results


def unflatten_dict(json_: Json, delimiter: str | None = None) -> SingleJson:
    unflattened = {}
    for key, value in json_.items():
        current = unflattened
        tokens = key.split(delimiter) if delimiter is not None else re.findall(r"\w+", key)

        if not tokens:
            tokens = [key]

        next_tokens = tokens[1:]
        next_tokens.append(value)

        for i, (index, next_token) in enumerate(
            zip(tokens, next_tokens, strict=False),
            1,
        ):
            if not isinstance(current, (dict, list)):
                continue

            next_value = next_token if i == len(tokens) else ([] if next_token.isdigit() else {})

            if isinstance(current, list):
                index = int(index)
                while index >= len(current):
                    current.append(next_value)

            elif index not in current:
                if delimiter is not None and not index:
                    index = delimiter

                current[index] = next_value

            current = current[index]

    return unflattened


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("---------------- Main - Param Init ----------------")
    json_str = siemplify.extract_action_param(
        param_name="JSON Object",
        is_mandatory=True,
        print_value=True,
    )
    delimiter = siemplify.extract_action_param(param_name="Delimiter", print_value=True)

    siemplify.LOGGER.info("---------------- Main - Started ----------------")
    result_value = True
    action_status = EXECUTION_STATE_COMPLETED
    output_message = f"Action '{ACTION_NAME}' finished successfully"
    siemplify.script_name = ACTION_NAME

    try:
        siemplify.LOGGER.info("Un-flattening JSON")
        json_object = json.loads(json_str)
        unflattened = unflatten_json(json_object, delimiter)
        siemplify.result.add_result_json(unflattened)

    except Exception as e:
        output_message = f"Error executing '{ACTION_NAME}'. Reason: "
        if isinstance(e, json.decoder.JSONDecodeError):
            output_message += "invalid JSON provided. Please check the structure."
        else:
            output_message += f"{e}"

        siemplify.LOGGER.exception(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        action_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info("Output Message: %s", output_message)
    siemplify.LOGGER.info("Result: %s", result_value)
    siemplify.LOGGER.info("Execution Status: %s", action_status)
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    main()
