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
from soar_sdk.SiemplifyDataModel import CustomList
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler


def get_custom_list_items_from_identifier_list(siemplify, category_name, identifiers):
    """Get a list of custom list items from category and entities list.
    :param category_name: the custom list category
    :param identifiers: a list of strings
    :return: a list of custom list item objects
    """
    return [CustomList(identifier, category_name, siemplify.environment) for identifier in identifiers]


def is_identifier_in_custom_list(siemplify, identifier, category):
    # Returns True if identifier in category (for current environment)
    custom_list_items = get_custom_list_items_from_identifier_list(
        siemplify,
        category,
        [identifier],
    )
    return siemplify.any_entity_in_custom_list(custom_list_items)


@output_handler
def main():
    siemplify = SiemplifyAction()

    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "output message :"
        result_value = 0

        category = siemplify.parameters.get("Category")
        try:
            identifier_list = json.loads(siemplify.parameters.get("IdentifierList"))
        except:
            identifier_list = siemplify.parameters.get("IdentifierList").split(",")
        identifier_list = [x.strip() for x in identifier_list]

        json_result = {}
        for identifier in identifier_list:
            if is_identifier_in_custom_list(siemplify, identifier, category):
                json_result[identifier] = True
                result_value += 1
            else:
                json_result[identifier] = False

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result),
            )

        output_message = f"Found {result_value} items in category {category}"

    except Exception:
        raise
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
