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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from csv_integration.core.constants import RECORDS_TABLE_NAME, SEARCH_BY_STRING_SCRIPT_NAME
from csv_integration.core.CSVManager import CSVManager, FILE_ENCODINGS_DEFAULT
from csv_integration.core.exceptions import CSVEncodingException
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from csv_integration.core.utils import get_encodings_or_raise, get_value_for_search, string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_BY_STRING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    csv_folder_or_file_path = extract_action_param(
        siemplify, is_mandatory=True, param_name="CSV Path", print_value=True
    )
    searchable_columns = string_to_multi_value(
        extract_action_param(siemplify, param_name="CSV Column", print_value=True),
        only_unique=True,
    )
    days_back = extract_action_param(siemplify, param_name="Days Back")
    return_the_first_row = extract_action_param(
        siemplify,
        param_name="Return the first row only",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    search_values = extract_action_param(
        siemplify, is_mandatory=True, param_name="Search Value", print_value=True
    )

    search_multiple_string = extract_action_param(
        siemplify,
        default_value=False,
        print_value=True,
        input_type=bool,
        param_name="Search Multiple Strings",
    )
    search_values = (
        string_to_multi_value(search_values, only_unique=True)
        if search_multiple_string
        else [search_values]
    )

    file_encodings_list = string_to_multi_value(
        extract_action_param(
            siemplify=siemplify,
            param_name="File Encoding Types",
            is_mandatory=True,
            default_value=",".join(FILE_ENCODINGS_DEFAULT),
            print_value=True,
        ),
        only_unique=True,
    )
    fields_to_return = string_to_multi_value(
        extract_action_param(
            siemplify=siemplify, param_name="Fields To Return", print_value=True
        ),
        only_unique=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    found_results, not_found_results, json_result, csv_table_data = set(), set(), {}, {}
    result_value = 0

    try:
        file_encodings_list = get_encodings_or_raise(siemplify, file_encodings_list)

        manager = CSVManager(siemplify)

        for csv_path in manager.get_relevant_csv_files(
            csv_folder_or_file_path, days_back=days_back
        ):
            siemplify.LOGGER.info(f'Processing "{csv_path}"')
            try:
                for search_value in search_values:
                    search_result = manager.search_in_csv(
                        csv_content=manager.read_csv(csv_path, file_encodings_list),
                        value_to_search=get_value_for_search(search_value),
                        return_the_first_match=return_the_first_row,
                        searchable_columns=searchable_columns,
                    )
                    siemplify.LOGGER.info(
                        f'Found {len(search_result)} rows in file "{csv_path}" for value "{search_value}"'
                    )
                    if not search_result:
                        not_found_results.add(search_value)
                        continue

                    found_results.add(search_value)
                    json_result[search_value] = json_result.get(search_value, [])
                    csv_table_data[search_value] = csv_table_data.get(search_value, [])

                    for csv_item in search_result:
                        csv_item.additional_data = {"file_source_path": csv_path}
                        csv_item.column_filter = fields_to_return
                        csv_item.get_process_data()
                        if csv_item.filtered_data_exist:
                            csv_table_data[search_value].append(csv_item.to_csv())

                        json_result[search_value].append(csv_item.to_json())

            except CSVEncodingException as e:
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    "Please provide right encoding's for reading csv file's"
                )
                raise

        if found_results:
            result_value = sum(map(len, json_result.values()))
            output_message = "Successfully found information about the following items:\n   {}\n".format(
                "\n   ".join(found_results)
            )
            not_found_results_in_all_files = [
                value for value in not_found_results if value not in found_results
            ]
            if not_found_results_in_all_files:
                output_message += "No information was found about the following items:\n   {}\n".format(
                    "\n   ".join(not_found_results_in_all_files)
                )
        else:
            output_message = "No information was found for the provided items."

        for search_value, csv_table in csv_table_data.items():
            if not csv_table:
                continue
            siemplify.result.add_data_table(
                RECORDS_TABLE_NAME.format(search_value), construct_csv(csv_table)
            )
        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

    except Exception as e:
        output_message = (
            f"Error executing action {SEARCH_BY_STRING_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
