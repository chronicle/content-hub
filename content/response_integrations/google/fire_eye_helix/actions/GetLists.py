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
from ..core.FireEyeHelixConstants import PROVIDER_NAME, GET_LISTS_SCRIPT_NAME
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

TABLE_HEADER = "FireEye Helix Lists"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_LISTS_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", is_mandatory=True
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    # Init Action Parameters
    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=False, print_value=True
    )
    short_name = extract_action_param(
        siemplify, param_name="Short Name", is_mandatory=False, print_value=True
    )
    active = extract_action_param(
        siemplify,
        param_name="Active",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    internal = extract_action_param(
        siemplify,
        param_name="Internal",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    protected = extract_action_param(
        siemplify,
        param_name="Protected",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    sort_by = extract_action_param(
        siemplify, param_name="Sort By", is_mandatory=False, print_value=True
    )
    sort_order = extract_action_param(
        siemplify, param_name="Sort Order", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Lists To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        results = manager.get_lists(
            name=name,
            short_name=short_name,
            active=active,
            internal=internal,
            protected=protected,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )

        if results:
            output_message = "Successfully returned lists from FireEye Helix."
            siemplify.result.add_result_json([result.to_json() for result in results])
            siemplify.result.add_entity_table(
                TABLE_HEADER, construct_csv([result.to_csv() for result in results])
            )
        else:
            output_message = "No lists were found that match the set criteria."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Get Lists". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
