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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, REMOVE_USER_FROM_GROUP_SCRIPT_NAME, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT
from ..core.utils import get_entity_original_identifier, convert_comma_separated_to_list
from ..core.exceptions import AzureADNotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_USER_FROM_GROUP_SCRIPT_NAME
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

    usernames = extract_action_param(
        siemplify, param_name="User Name", print_value=True
    )
    group_name = extract_action_param(
        siemplify, param_name="Group Name", print_value=True, is_mandatory=False
    )
    group_id_param = extract_action_param(
        siemplify, param_name="Group ID", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    usernames = convert_comma_separated_to_list(usernames)

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = True
    successful_users, failed_users, not_found_users = [], [], []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.USER
    ]

    try:
        if not group_name and not group_id_param:
            raise Exception(f'Either "Group ID" or "Group Name" needs to be provided.')

        manager = AzureADManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            verify_ssl=verify_ssl,
            api_root=api_root,
            login_api_root=login_api_root,
            force_check_connectivity=True,
        )

        if not usernames:
            for entity in suitable_entities:
                usernames.append(get_entity_original_identifier(entity))

        group_id = group_id_param
        if not group_id_param:
            group_id = manager.get_group_id(group_name=group_name)

        if not group_id:
            raise Exception(
                f"Provided group name {group_name} was not found in the {INTEGRATION_DISPLAY_NAME}."
            )

        for username in usernames:
            siemplify.LOGGER.info(f"Started processing username: {username}")
            try:
                user_id = manager.get_user_id(user_principal_name=username)
                manager.remove_user_from_group(group_id=group_id, user_id=user_id)
                successful_users.append(username)
            except AzureADNotFoundError as e:
                failed_users.append(username)
                siemplify.LOGGER.error(f"An error occurred on entity {username}")
                siemplify.LOGGER.exception(e)
            except Exception as e:
                not_found_users.append(username)
                siemplify.LOGGER.error(f"An error occurred on entity {username}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {username}")

        group_value_for_messages = group_id_param if group_id_param else group_name

        if successful_users:
            output_message += (
                f"Successfully removed the following users from the Azure AD group "
                f"{group_value_for_messages}:\n {', '.join(successful_users)}\n"
            )

            if failed_users:
                output_message += (
                    f"\nThe following users were not found in the Azure AD group "
                    f"{group_value_for_messages} members list: \n{', '.join(failed_users)}\n"
                )
            if not_found_users:
                output_message += (
                    f"\nThe following users were not found in "
                    f"{INTEGRATION_DISPLAY_NAME}: \n{', '.join(not_found_users)}\n"
                )

        else:
            if not_found_users and not failed_users:
                output_message = f"None of the provided users were found in {INTEGRATION_DISPLAY_NAME}."
            if failed_users and not not_found_users:
                output_message = (
                    f"None of the provided users were found in the Azure AD group "
                    f"{group_value_for_messages} members list."
                )
            if failed_users and not_found_users:
                output_message += (
                    f"\nThe following users were not found in the Azure AD group "
                    f"{group_value_for_messages} members list: \n{', '.join(failed_users)}\n"
                )
                output_message += (
                    f"\nThe following users were not found in "
                    f"{INTEGRATION_DISPLAY_NAME}: \n{', '.join(not_found_users)}\n"
                )
            if not not_found_users and not failed_users:
                output_message = "No usernames were provided in the action."
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {REMOVE_USER_FROM_GROUP_SCRIPT_NAME}. Reason: {e}"
        )
        result_value = False
        siemplify.LOGGER.error(
            f"General error performing action {REMOVE_USER_FROM_GROUP_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
