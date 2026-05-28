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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AttivoManager import AttivoManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_CRITICAL_THREATPATH_SCRIPT_NAME,
    FILTER_KEY_SELECT_ONE_FILTER,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    FILTER_KEY_MAPPING,
)
from TIPCommon import construct_csv


TABLE_NAME = "Available ThreatPaths"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_CRITICAL_THREATPATH_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if filter_key == FILTER_KEY_SELECT_ONE_FILTER and (
            filter_logic == EQUAL_FILTER or filter_logic == CONTAINS_FILTER
        ):
            raise Exception(
                f'you need to select a field from the "Filter Key" parameter.'
            )

        if limit is not None:
            if limit < 1:
                raise Exception(
                    f'Invalid value was provided for "Max Records to Return": {limit}. '
                    f"Positive number should be provided"
                )

        manager = AttivoManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Retrieving information about critical ThreatPaths...")
        threatpaths = manager.get_critical_threatpaths()
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                threatpaths = [
                    path
                    for path in threatpaths
                    if getattr(path, FILTER_KEY_MAPPING.get(filter_key)) == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                threatpaths = [
                    path
                    for path in threatpaths
                    if filter_value in getattr(path, FILTER_KEY_MAPPING.get(filter_key))
                ]

        threatpaths = threatpaths[:limit] if limit else threatpaths

        if threatpaths:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([path.to_csv() for path in threatpaths])
            )
            siemplify.result.add_result_json([path.to_json() for path in threatpaths])
            output_message = f"Successfully found critical ThreatPaths for the provided criteria in {INTEGRATION_DISPLAY_NAME}"
        else:
            result = False
            output_message = f"No ThreatPaths were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}"

        if (
            (filter_logic == EQUAL_FILTER or filter_logic == CONTAINS_FILTER)
            and filter_key != FILTER_KEY_SELECT_ONE_FILTER
            and filter_value is None
        ):
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value. '

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_CRITICAL_THREATPATH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_CRITICAL_THREATPATH_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
