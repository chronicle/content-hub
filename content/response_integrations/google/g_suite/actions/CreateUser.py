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
from TIPCommon.extraction import extract_action_param

from ..core.action_init import create_api_client
from ..core.consts import INTEGRATION_NAME, CREATE_USER_SCRIPT_NAME
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {CREATE_USER_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    given_name = extract_action_param(
        siemplify, param_name="Given Name", is_mandatory=True, print_value=True
    )
    family_name = extract_action_param(
        siemplify, param_name="Family Name", is_mandatory=True, print_value=True
    )
    password = extract_action_param(
        siemplify, param_name="Password", is_mandatory=True, print_value=False
    )
    primary_email = extract_action_param(
        siemplify, param_name="Email Address", is_mandatory=True, print_value=True
    )
    phone = extract_action_param(
        siemplify, param_name="Phone", is_mandatory=False, print_value=True
    )
    gender = extract_action_param(
        siemplify, param_name="Gender", is_mandatory=False, print_value=True
    )
    department = extract_action_param(
        siemplify, param_name="Department", is_mandatory=False, print_value=True
    )
    organization = extract_action_param(
        siemplify, param_name="Organization", is_mandatory=False, print_value=True
    )
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=False, print_value=True
    )
    change_password_on_first_login = extract_action_param(
        siemplify,
        param_name="Change Password At Next Login",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        gsuite_manager = create_api_client(siemplify)
        user = gsuite_manager.create_user(
            given_name=given_name,
            family_name=family_name,
            password=password,
            primary_email=primary_email,
            change_password_at_next_login=change_password_on_first_login,
            phone=phone,
            organization=organization,
            department=department,
            gender=gender,
            note=note,
        )
        siemplify.result.add_result_json(user.as_json())
        output_message = (
            f"Successfully created user {given_name} {family_name} with"
            f"primary email address {primary_email}"
        )
    except Exception as error:
        output_message = (
            f"Error executing action {CREATE_USER_SCRIPT_NAME}. Reason: {error}"
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
