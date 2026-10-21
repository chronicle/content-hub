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
from itertools import groupby

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.CBCloudManager import CBCloudManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_REPUTATION_OVERRIDES_SCRIPT_NAME,
    NOT_SPECIFIED,
    ASC,
    MAPPED_SORT_ORDER,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_REPUTATION_OVERRIDES_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    reputation_override_list = extract_action_param(
        siemplify,
        param_name="Reputation Override List",
        is_mandatory=False,
        default_value=NOT_SPECIFIED,
        print_value=True,
    )
    reputation_override_type = extract_action_param(
        siemplify,
        param_name="Reputation Override Type",
        is_mandatory=False,
        default_value=NOT_SPECIFIED,
        print_value=True,
    )
    rows_sort_order = extract_action_param(
        siemplify,
        param_name="Rows Sort Order",
        is_mandatory=False,
        default_value=ASC,
        print_value=True,
    )

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        start_from_row = extract_action_param(
            siemplify,
            param_name="Start from Row",
            is_mandatory=False,
            default_value=0,
            input_type=int,
            print_value=True,
        )
        max_rows_to_return = extract_action_param(
            siemplify,
            param_name="Max Rows to Return",
            is_mandatory=False,
            default_value=50,
            input_type=int,
            print_value=True,
        )
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if start_from_row < 0:
            raise Exception('"Start from Row" must be greater than or equal to 0.')
        if max_rows_to_return <= 0:
            raise Exception('"Max Rows to Return" must be greater than 0.')

        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        try:
            reputations = manager.list_reputation_overrides(
                override_list=(
                    None
                    if reputation_override_list == NOT_SPECIFIED
                    else reputation_override_list
                ),
                override_type=(
                    None
                    if reputation_override_type == NOT_SPECIFIED
                    else reputation_override_type
                ),
                start_row=start_from_row,
                max_rows=max_rows_to_return,
                sort_order=MAPPED_SORT_ORDER.get(rows_sort_order),
                sort_field="create_time",
            )
            if reputations:
                output_message = "Reputation overrides found."
                result_value = True
                for rep_type, group in groupby(
                    sorted(reputations, key=lambda x: x.override_type),
                    key=lambda x: x.override_type,
                ):
                    siemplify.result.add_data_table(
                        f"Found {rep_type} Reputation",
                        construct_csv([rep.to_csv() for rep in list(group)]),
                    )
                siemplify.result.add_result_json(
                    {"results": [rep.to_json() for rep in reputations]}
                )
            else:
                output_message = "No reputation overrides were created."
        except Exception as error:
            output_message = f"Failed to list reputation overrides. Reason: {error}"
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except Exception as e:
        output_message = f"Error executing action {LIST_REPUTATION_OVERRIDES_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
