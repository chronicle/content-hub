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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_action_param, extract_configuration_param, construct_csv
from ..core.constants import (
    DEFAULT_MAX_RECORDS_TO_RETURN,
    INTEGRATION_NAME,
    LIST_POLICIES_SCRIPT_NAME,
    POSSIBLE_POLICY_FILTER_KEYS,
)
from ..core.AutomoxManager import AutomoxManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_POLICIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
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
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", is_mandatory=False, print_value=True
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", is_mandatory=False, print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", is_mandatory=False, print_value=True
    )
    max_records_to_return = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        input_type=int,
        default_value=DEFAULT_MAX_RECORDS_TO_RETURN,
        is_mandatory=False,
        print_value=True,
    )

    filter_key = POSSIBLE_POLICY_FILTER_KEYS.get(filter_key)
    filter_logic = filter_logic if filter_logic != "Not Specified" else None
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if not filter_value:
            output_message += "The filter was not applied, because parameter “Filter Value” has an empty value."
        elif not filter_logic:
            output_message += "The filter was not applied, because parameter “Filter Logic” is not specified."
        elif not filter_key:
            raise ValueError(
                "you need to select a field from the “Filter Key” parameter."
            )

        if not max_records_to_return >= 1:
            raise ValueError(
                f"Invalid value was provided for “Max Records to Return”: {max_records_to_return}. "
                f"Positive number should be provided."
            )

        manager = AutomoxManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info("Getting policies from Automox")
        policies = manager.get_policies(
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
            max_records_to_return=max_records_to_return,
        )
        if policies:
            siemplify.LOGGER.info(
                "Successfully found policies for the provided criteria in Automox"
            )
            output_message += (
                "Successfully found policies for the provided criteria in Automox"
            )
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            siemplify.result.add_result_json([policy.as_json() for policy in policies])
            siemplify.result.add_data_table(
                title="Available Policies",
                data_table=construct_csv([policy.as_csv() for policy in policies]),
            )
        else:
            siemplify.LOGGER.info(
                "No policies were found for the provided criteria in Automox."
            )
            output_message += (
                "No policies were found for the provided criteria in Automox."
            )
            status = EXECUTION_STATE_COMPLETED
            result_value = False
    except Exception as e:
        output_message = (
            f"Error executing action “{LIST_POLICIES_SCRIPT_NAME}”. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
