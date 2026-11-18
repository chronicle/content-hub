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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_init import create_api_client
from ..core.consts import INTEGRATION_NAME, CREATE_OU_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {CREATE_OU_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    customer_id = extract_action_param(
        siemplify, param_name="Customer ID", is_mandatory=True, print_value=True
    )
    ou_name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=False, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )
    parent_path = extract_action_param(
        siemplify, param_name="Parent OU Path", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        gsuite_manager = create_api_client(siemplify)
        ou = gsuite_manager.create_ou(
            name=ou_name,
            description=description,
            parent_path=parent_path,
            customer_id=customer_id,
        )
        siemplify.result.add_result_json(ou.as_json())
        output_message = (
            f"Successfully created organization unit {ou_name} for customer id \
            {customer_id} with organization unit "
            f"parent path {parent_path}"
        )
    except Exception as error:
        output_message = (
            f"Error executing action {CREATE_OU_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
