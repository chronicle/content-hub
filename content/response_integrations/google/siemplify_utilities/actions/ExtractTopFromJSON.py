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
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SiemplifyUtilitiesManager import SiemplifyUtilitiesManager
from soar_sdk.SiemplifyUtils import output_handler

ACTION_NAME = "SiemplifyUtilities_Extract Top From JSON"
WILD_CARD_SIGN = "*"
JSON_HEADER_PATTERN = "Branch No.{0}"  # Brunch Number.


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    # Parameters.
    json_data = json.loads(siemplify.parameters.get("JSON Data", {}))
    nested_key = siemplify.parameters.get("Key To Sort By", "").split(".")
    field_type = siemplify.parameters.get("Field Type", "number")
    reverse = (
        siemplify.parameters.get("Reverse (DESC -> ASC)", "false").lower() == "true"
    )
    top_rows = int(siemplify.parameters.get("Top Rows", 3))

    branches = SiemplifyUtilitiesManager.fetch_branches_from_dict(
        json_data, nested_key, WILD_CARD_SIGN
    )

    sorted_branches = SiemplifyUtilitiesManager.sort_list_of_dicts_by_nested_key(
        branches,
        nested_key,
        field_type,
        reverse=reverse,
        wild_card_value=WILD_CARD_SIGN,
    )

    top_sorted_branches = sorted_branches[:top_rows]

    for index, branch in enumerate(top_sorted_branches):
        siemplify.result.add_json(
            JSON_HEADER_PATTERN.format(index + 1), json.dumps(branch)
        )

    if sorted_branches:
        output_message = f"Top {len(top_sorted_branches)} branches presented."
    else:
        output_message = "No branches were found."

    siemplify.result.add_result_json(top_sorted_branches)
    siemplify.end(output_message, json.dumps(top_sorted_branches))


if __name__ == "__main__":
    main()
