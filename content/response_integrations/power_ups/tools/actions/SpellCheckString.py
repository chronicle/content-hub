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

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from spellchecker import SpellChecker


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = "output message :"  # human readable message, showed in UI as the action result
    result_value = None  # Set a simple result value, used for playbook if\else and placeholders.
    json_result = {}
    spell = SpellChecker()
    input_string = siemplify.extract_action_param(
        "String",
        default_value="",
        print_value=True,
    )
    if input_string == "":
        result_value = 0
        output_message = "No input to test."
    else:
        json_result["input_string"] = input_string
        string_no_punctuation = re.sub(r"[^\w\s]", "", input_string)
        input_words = string_no_punctuation.split()
        json_result["total_words"] = len(input_words)

        misspelled = spell.unknown(input_words)
        json_result["total_misspelled_words"] = 0
        corrected = input_string
        json_result["misspelled_words"] = []
        for word in misspelled:
            correct = {
                "misspelled_word": word,
                "correction": spell.correction(word) or word,
            }
            if correct["misspelled_word"] != correct["correction"]:
                json_result["total_misspelled_words"] += 1
                json_result["misspelled_words"].append(correct)
                corrected = re.sub(rf"\b{word}\b", correct["correction"], corrected)
        json_result["accuracy"] = int(
            (len(input_words) - json_result["total_misspelled_words"]) / len(input_words) * 100,
        )
        json_result["corrected_string"] = corrected
        result_value = json_result["accuracy"]
        siemplify.result.add_result_json(json_result)
        output_message = f"The input string is {json_result['accuracy']}% accurate"
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
