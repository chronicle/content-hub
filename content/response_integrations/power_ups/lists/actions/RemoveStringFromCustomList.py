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
from soar_sdk.SiemplifyDataModel import CustomList
from soar_sdk.SiemplifyUtils import output_handler


def get_custom_list_items(siemplify, category_name, input_string):
    """Get a list of custom list items from category and entities list.
    :param category_name: the custom list category
    :param entities: a list of entities
    :return: a list of custom list item objects
    """
    custom_list_items = []
    custom_list_items.append(
        CustomList(input_string, category_name, siemplify.environment),
    )
    return custom_list_items


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        category = siemplify.parameters.get("Category")
        list_item = siemplify.parameters.get("ListItem")
        custom_list_items = get_custom_list_items(siemplify, category, list_item)
        siemplify.remove_entities_from_custom_list(custom_list_items)
        output_message = f"Removed {list_item} from category {category}"

    except Exception:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message += "output message :\n unknown failure"

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
