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
from ..core.AzureADManager import AzureADManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from ..core.constants import INTEGRATION_NAME, RESET_USER_PASSWORD_SCRIPT_NAME, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from ..core.utils import get_entity_original_identifier
from ..core.exceptions import AzurePasswordComplexityError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = RESET_USER_PASSWORD_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Directory ID",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )

    username = extract_action_param(
        siemplify,
        param_name="Username",
        is_mandatory=False,
    )
    new_password = extract_action_param(
        siemplify, param_name="Password", is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = True
    successful_entities, failed_entities, failed_password_entities = [], [], []

    # If the action input parameter `Username` is provided, process only that username
    if username:
        target_users = [
            user.strip() for user in username.split(",") if user.strip()
        ]
        siemplify.LOGGER.info(f"Using input parameter 'Username': {username}")
    else:
        target_users = [
            get_entity_original_identifier(entity)
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.USER
        ]

    try:
        manager = AzureADManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            verify_ssl=verify_ssl,
            api_root=api_root,
            login_api_root=login_api_root,
            force_check_connectivity=True,
        )

        for user in target_users:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                time_out = convert_unixtime_to_datetime(
                    siemplify.execution_deadline_unix_time_ms
                )
                siemplify.LOGGER.error(
                    f"Timed out. Execution deadline "
                    f"({time_out}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            siemplify.LOGGER.info(f"Started processing user: {user}")

            try:
                manager.reset_user_password(user, new_password)
                successful_entities.append(user)
            except AzurePasswordComplexityError as e:
                failed_password_entities.append(user)
                siemplify.LOGGER.error(
                    f"Password complexity error for user {user}: {e}"
                )
                siemplify.LOGGER.exception(e)
            except Exception as e:
                failed_entities.append(user)
                siemplify.LOGGER.error(f"An error occurred on user {user}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing user: {user}")

        if failed_password_entities:
            output_message = (
                "Failed to execute the action. The specified password does not comply "
                "with password complexity requirements. Please provide a different "
                "password."
            )
            result_value = False
            status = EXECUTION_STATE_FAILED
        elif successful_entities:
            output_message += (
                "Password was successfully changed for the following users:"
                f"\n{', '.join(successful_entities)}\n")

            if failed_entities:
                output_message += (
                    "Failed to process the following users:"
                    f"\n{', '.join(failed_entities)}\n"
                )
        else:
            output_message = "No user passwords were reset."
            result_value = False

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {RESET_USER_PASSWORD_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"An error occurred while running action: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
