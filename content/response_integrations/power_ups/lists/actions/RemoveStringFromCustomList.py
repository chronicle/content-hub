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


def remove_entities_from_custom_list(siemplify, custom_list_items):
    """Remove the entities from the custom list with the given category.
    :param custom_list_items: a list of custom list items
    :return: None
    """
    custom_list_items_data = []
    for cli in custom_list_items:
        custom_list_items_data.append(cli.__dict__)

    address = f"{siemplify.API_ROOT}/{'external/v1/sdk/RemoveEntitiesFromCustomList?format=snake'}"
    response = siemplify.session.post(address, json=custom_list_items_data)
    siemplify.validate_siemplify_error(response)

    custom_list_dicts = response.json()

    # Create CustomList objects from the custom list dicts
    custom_lists = [
        CustomList(**custom_list_dict) for custom_list_dict in custom_list_dicts
    ]
    return custom_lists


@output_handler
def main():
    siemplify = SiemplifyAction()

    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "output message :"
        category = siemplify.parameters.get("Category")
        list_item = siemplify.parameters.get("ListItem")
        custom_list_items = get_custom_list_items(siemplify, category, list_item)
        remove_entities_from_custom_list(siemplify, custom_list_items)
        output_message = f"Removed {list_item} from category {category}"

    except Exception:
        raise
        status = EXECUTION_STATE_FAILED
        output_message += "\n unknown failure"

    siemplify.end(output_message, True, status)


if __name__ == "__main__":
    main()
