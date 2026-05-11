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
import copy

from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SiemplifyUtilitiesManager import SiemplifyUtilitiesManager
from soar_sdk.SiemplifyUtils import output_handler

from ..core.exceptions import SiemplifyUtilitiesError

ACTION_NAME = "Siemplify_List Operations"

OPERATORS = ["intersection", "union", "subtract", "xor"]

RESULT_JSON = {"results": {"count": 0, "data": []}}


def validate_operator(operator: str) -> str:
    """
    Validate operator string.

    Args:
        operator: Operator to validate.

    Returns:
        A valid operator in string format
    """
    if operator not in OPERATORS:
        raise SiemplifyUtilitiesError(
            f"Operator is not valid, must be one of {','.join(OPERATORS)}"
        )
    return operator


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    result_json = copy.deepcopy(RESULT_JSON)

    # Parameters.
    delimiter = siemplify.parameters.get("Delimiter", ",")
    first_list = siemplify.parameters.get("First List", "").split(delimiter)
    second_list = siemplify.parameters.get("Second List", "").split(delimiter)
    operator = validate_operator(siemplify.parameters.get("Operator"))

    if operator == "intersection":
        result_list = SiemplifyUtilitiesManager.intersect_lists(first_list, second_list)
    elif operator == "union":
        result_list = SiemplifyUtilitiesManager.union_lists(first_list, second_list)
    elif operator == "subtract":
        result_list = SiemplifyUtilitiesManager.subtract_lists(first_list, second_list)
    else:
        result_list = SiemplifyUtilitiesManager.xor_lists(first_list, second_list)

    output_message = (
        f"Performed {operator} on {first_list}, {second_list}\nThe result is:"
        f" {result_list}"
    )

    result_json["results"]["count"] = len(result_list)
    result_json["results"]["data"] = delimiter.join(result_list)

    siemplify.result.add_result_json(result_json)
    siemplify.end(output_message, delimiter.join(result_list))


if __name__ == "__main__":
    main()
