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
from TIPCommon.rest.soar_api import get_traking_list_record


@output_handler
def main():
    siemplify = SiemplifyAction()

    categories = siemplify.extract_action_param(
        "Categories",
        print_value=True,
        default_value=None,
    )
    string = siemplify.extract_action_param(
        "String to Search",
        print_value=True,
        default_value=None,
    )

    list_categories = (
        [category.strip() for category in categories.split(",") if category.strip()]
        if categories
        else []
    )
    status = EXECUTION_STATE_COMPLETED
    output_message = "Failed to get custom list items with provided parameters."
    result_value = True

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Getting custom list records")
        records = get_traking_list_record(siemplify, list_categories)
        records = records.get("custom_lists", []) if isinstance(records, dict) else records

        siemplify.LOGGER.info("Searching records for match criteria")
        if list_categories:
            relevant_records = []
            for record in records:
                if record["category"] in list_categories:
                    relevant_records.append(record)
        else:
            relevant_records = records

        json_result = []
        match_records = []
        if relevant_records:
            if string:
                for record in relevant_records:
                    if string in record["entityIdentifier"]:
                        match_records.append(record)
            else:
                match_records = relevant_records
        if match_records:
            siemplify.LOGGER.info(f"Found {len(match_records)} matching records")
            json_result = match_records
        else:
            siemplify.LOGGER.info("No matching records found")
            result_value = False

        if json_result:
            siemplify.result.add_result_json(json_result)
            output_message = f"Found {len(match_records)} matching records"
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = "Failed to find records in custom lists"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
