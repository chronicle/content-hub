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

"""AtlassianConfluenceServer - List Pages."""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param

from ..core.ConfluenceManager import ConfluenceManager
from ..core.constants import (
    FILTER_KEY_VALUES,
    FILTER_STRATEGY_MAPPING,
    INTEGRATION_IDENTIFIER,
    LIST_PAGES_SCRIPT_NAME,
    TABLE_NAME,
)
from ..core.exceptions import ConfluenceFilterKeyParamError, ConfluenceInvalidLimitError
from ..core.utils import construct_ordered_csv, get_configuration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_PAGES_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")

    # Integration Configuration
    (api_root, username, password, api_token, verify_ssl) = get_configuration_params(
        siemplify_action_instance=siemplify
    )

    # Action Parameters
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", is_mandatory=False, print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", is_mandatory=False, print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", is_mandatory=False, print_value=True
    )
    max_records = extract_action_param(
        siemplify,
        param_name="Max Records to Return",
        input_type=int,
        is_mandatory=False,
        default_value=50,
        print_value=True,
    )

    siemplify.LOGGER.info("--------------- Main - Started ---------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_result = {}

    try:
        filter_val = FILTER_KEY_VALUES.get(filter_key)
        filter_stat = FILTER_STRATEGY_MAPPING.get(filter_logic)
        if not filter_val and filter_stat:
            raise ConfluenceFilterKeyParamError(
                "you need to select a field from the 'Filter Key' parameter."
            )

        if max_records < 1:
            raise ConfluenceInvalidLimitError(
                "Invalid value was provided for 'Max Records to "
                f"Return': {max_records}. Positive number should be provided."
            )

        confluence_manager = ConfluenceManager(
            api_root,
            username,
            password,
            api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        list_objects = confluence_manager.list_pages(
            max_records, filter_key, filter_logic, filter_value
        )

        csv_data = construct_ordered_csv(
            [list_object.to_table() for list_object in list_objects]
        )
        if list_objects:
            siemplify.result.add_data_table(TABLE_NAME, csv_data)
            json_result = {
                "results": [list_object.to_json() for list_object in list_objects]
            }
            siemplify.result.add_result_json(json_result)
            output_message = (
                "Successfully found pages for the provided "
                f"criteria in {INTEGRATION_IDENTIFIER}."
            )

        else:
            result = False
            output_message = (
                "No pages were found for the provided criteria"
                f" in {INTEGRATION_IDENTIFIER}."
            )

        if filter_val and filter_stat and not filter_value:
            output_message += (
                "\nThe filter was not applied, because parameter"
                " 'Filter Value' has an empty value."
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_PAGES_SCRIPT_NAME}"
        )
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{siemplify.script_name}'. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
