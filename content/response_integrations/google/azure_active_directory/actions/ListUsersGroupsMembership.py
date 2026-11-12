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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.AzureADManager import AzureADManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.constants import FILTER_LOGIC_CONTAINS, FILTER_LOGIC_EQUALS, SELECT_ONE_FILTER_KEY, INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, LIST_USERS_GROUPS_MEMBERSHIPS_SCRIPT_NAME, GROUP_FILTER_KEYS_MAPPING, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT
from ..core.utils import convert_comma_separated_to_list
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.utils import filter_items


SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_USERS_GROUPS_MEMBERSHIPS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # configuration parameters
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

    # action parameters
    username_string = extract_action_param(
        siemplify, param_name="User Name", print_value=True
    )
    only_security_enabled_groups = extract_action_param(
        siemplify,
        param_name="Return Only Security Enabled Groups",
        input_type=bool,
        print_value=True,
    )
    detailed_groups_information = extract_action_param(
        siemplify,
        param_name="Return Detailed Groups Information",
        input_type=bool,
        print_value=True,
    )

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
        default_value=50,
        input_type=int,
        print_value=True,
    )

    usernames = convert_comma_separated_to_list(username_string)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    no_groups_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Records to Return": {limit}. Positive number '
                f"should be provided"
            )

        if filter_key == SELECT_ONE_FILTER_KEY and (
            filter_logic == FILTER_LOGIC_EQUALS or filter_logic == FILTER_LOGIC_CONTAINS
        ):
            raise Exception(
                f'you need to select a field from the "Filter Key" parameter'
            )

        manager = AzureADManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            verify_ssl=verify_ssl,
            api_root=api_root,
            login_api_root=login_api_root,
            force_check_connectivity=True,
        )

        usernames = (
            usernames
            if usernames
            else [entity.identifier for entity in suitable_entities]
        )

        groups = {
            item.id: item
            for item in filter_items(
                manager.get_list_of_all_groups(),
                GROUP_FILTER_KEYS_MAPPING.get(filter_key),
                filter_value,
                filter_logic,
            )
        }

        for username in usernames:
            siemplify.LOGGER.info(f"\nStarted processing entity: {username}")

            try:
                user_groups_ids = manager.get_user_groups(
                    username, only_security_enabled_groups, limit
                )
                user_groups = [
                    groups.get(user_groups_id)
                    for user_groups_id in user_groups_ids
                    if groups.get(user_groups_id)
                ]

                if user_groups:
                    json_results[username] = [
                        user_group.as_json(detailed_groups_information)
                        for user_group in user_groups
                    ]
                    siemplify.result.add_data_table(
                        f"{username} Groups Memberships",
                        construct_csv(
                            [
                                user_group.to_table(detailed_groups_information)
                                for user_group in user_groups
                            ]
                        ),
                    )

                    successful_entities.append(username)
                else:
                    no_groups_entities.append(username)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entity: {username}: Error is: {e}"
                )
                failed_entities.append(username)

            siemplify.LOGGER.info(f"Finished processing entity {username}\n")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully found groups for the provided criteria for the following entities: \n{}".format(
                "\n".join(successful_entities)
            )

        if failed_entities:
            output_message += (
                "\nThe following entities were not found in the {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME, "\n".join(failed_entities)
                )
            )

        if no_groups_entities:
            output_message += "\nNo groups were found for the provided criteria for the following entities: \n{}".format(
                "\n".join(no_groups_entities)
            )

        if not successful_entities:
            result_value = False
            output_message = f"No groups were found in {INTEGRATION_DISPLAY_NAME}."

        if filter_value is None and filter_key != SELECT_ONE_FILTER_KEY:
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"Error executing action {LIST_USERS_GROUPS_MEMBERSHIPS_SCRIPT_NAME}."
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {LIST_USERS_GROUPS_MEMBERSHIPS_SCRIPT_NAME}. Reason: {e}."

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
