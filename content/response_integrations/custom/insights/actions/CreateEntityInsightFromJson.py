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
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import parse_raw_message

# CONSTS
OPEN_PH_PARENTHASIS = "{"
CLOSE_PH_PARENTHASIS = "}"
PIPE = "|"

DEBUG = True


def print_debug(to_print, function=""):
    if DEBUG:
        print(f"{function} DEBUG: {to_print}")


def find_key_path_in_json(key_path, json_data):
    """Finds the relevant key_path in a json object.
    If list encountered, this function will return a list of values, one for each
    match in each of the list's elements (using the rest of the keys)
    """
    return find_key_path_recursive(key_path, json_data)


def find_key_path_recursive(key_list, current_json, iteration=0):
    if key_list:
        if isinstance(current_json, list):
            if key_list:
                ret_list = []
                for element in current_json:
                    ret_list.extend(
                        find_key_path_recursive(
                            key_list,
                            element,
                            iteration=iteration + 1,
                        ),
                    )
                return ret_list

            return current_json
        if isinstance(current_json, dict):
            if key_list[0] in current_json:
                return find_key_path_recursive(
                    key_list[1:],
                    current_json[key_list[0]],
                    iteration=iteration + 1,
                )
            return []
    else:
        if isinstance(current_json, dict):
            return [current_json]
        if isinstance(current_json, list):
            return current_json
        return [
            f"{current_json}",
        ]  # Found val, return it. Format to make everything into string


def GetEntityByString(identifier, entities):
    for ent in entities:
        if identifier.lower() == ent.identifier.lower():
            return ent
    return None


def evaluate_function(val, func_name, func_values):
    if func_name == "default":
        if not val:
            return func_values[0]
        return val
    if func_name == "str":
        return str(val)
    if func_name == "join":
        delimeter = ",".join(func_values)
        return delimeter.join(val)
    # elif func_name == "ph":
    #     pass
    raise Exception(f"Unknown pipe function: {func_name}")


def parse_placeholder(curr_json, placeholder, pipe):
    pipes = [x.strip() for x in placeholder.split(pipe)]

    val = None
    for i, function_str in enumerate(pipes):
        # print_debug("function_str: {}, curr_json: {}".format(function_str, curr_json), "iteration {}".format(i))
        first_split = function_str.strip().split("(")
        if len(first_split) > 2:
            raise Exception(f"Bad format for pipe function: {function_str}")
        if len(first_split) == 1:
            # Assuming key_path here
            if isinstance(curr_json, list) or isinstance(curr_json, dict):
                curr_json = find_key_path_in_json([function_str], curr_json)
            else:
                return None  # cant find "keys" in a string
        else:  # len is 2
            func_name = first_split[0]
            func_values_string = first_split[1].split(")")[0]
            func_values = [x for x in func_values_string.split(",")]
            curr_json = evaluate_function(curr_json, func_name, func_values)

    return curr_json


def parse_raw_message_old(
    curr_json,
    raw_message,
    pipe=PIPE,
    open_ph=OPEN_PH_PARENTHASIS,
    close_ph=CLOSE_PH_PARENTHASIS,
):
    new_message = ""
    first_break = raw_message.split(open_ph)
    new_message += first_break[0]
    i = 1
    while i < len(first_break):
        second_break = first_break[i].split(close_ph)
        if len(second_break) < 2:
            raise Exception(f"Missing close PH: '{close_ph}'")
        message_shard = parse_placeholder(curr_json, second_break[0], pipe)
        new_message += str(message_shard) + close_ph.join(second_break[1:])
        i += 1

    return new_message


def get_relevant_json(entity, identifier_key_path, json_input):
    for curr_json in json_input:
        json_identifier = find_key_path_in_json(identifier_key_path, curr_json)[0]
        if json_identifier.lower() == entity.identifier.lower():
            return curr_json
    return {}


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = "No insight created"
    result_value = False

    try:
        json_input = json.loads(siemplify.parameters.get("JSON"))
    except:
        siemplify.end("Failed to load JSON", "Failed", EXECUTION_STATE_FAILED)
    identifier_key_path_raw = siemplify.parameters.get("Identifier KeyPath")
    identifier_key_path = [x.strip() for x in identifier_key_path_raw.split(".")]

    raw_message = siemplify.parameters.get("Message")

    try:
        successful_entities = []
        for entity in siemplify.target_entities:
            relevant_json = get_relevant_json(entity, identifier_key_path, json_input)

            if relevant_json:
                message = parse_raw_message(relevant_json, raw_message)
                print_debug(message, "final message")
                if message:
                    output_message = message
                    siemplify.add_entity_insight(
                        entity,
                        message,
                        triggered_by=siemplify.parameters.get(
                            "Triggered By",
                            "Siemplify",
                        ),
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
