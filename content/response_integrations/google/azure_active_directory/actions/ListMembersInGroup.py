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
from soar_sdk.SiemplifyUtils import output_handler
from ..core.AzureADManager import AzureADManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.constants import FILTER_LOGIC_CONTAINS, FILTER_LOGIC_EQUALS, SELECT_ONE_FILTER_KEY, INTEGRATION_NAME, LIST_MEMBERS_IN_GROUP_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_MEMBERS_IN_GROUP_SCRIPT_NAME
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

    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        default_value=50,
        input_type=int,
        print_value=True,
    )

    group_name = extract_action_param(
        siemplify, param_name="Group Name", print_value=True, is_mandatory=False
    )

    group_id_param = extract_action_param(
        siemplify, param_name="Group ID", print_value=True, is_mandatory=False
    )

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )

    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True
    )

    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    list_of_groups_csv = []
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    group_id = group_id_param

    try:
        if not group_name and not group_id_param:
            raise Exception(f'Either "Group ID" or "Group Name" needs to be provided.')

        if limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Records to Return": {limit}. Positive number should be provided.'
            )

        if filter_key == SELECT_ONE_FILTER_KEY and (
            filter_logic == FILTER_LOGIC_EQUALS or filter_logic == FILTER_LOGIC_CONTAINS
        ):
            raise Exception(
                f'you need to select a field from the "Filter Key" parameter.'
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
        if not group_id_param:
            if group := manager.get_group_by_name(group_name):
                group_id = group.id

        if group_id is None:
            raise Exception(
                f"Provided group name {group_name} was not found in the {INTEGRATION_DISPLAY_NAME}."
            )

        group_members = manager.get_group_members(
            filter_value=filter_value,
            filter_logic=filter_logic,
            group_id=group_id,
            limit=limit,
            filter_key=filter_key,
        )

        if not group_members:
            result_value = False
            output_message = (
                "No members were found for the provided criteria in Azure AD group."
            )
        else:
            output_message = "Successfully found members for the provided criteria in Azure AD group."
            json_result = [member.raw_data for member in group_members]
            siemplify.result.add_result_json(json_result)
            siemplify.result.add_data_table(
                "Available members of the group",
                construct_csv(
                    [
                        member.to_member_csv(fields="All Fields")
                        for member in group_members
                    ]
                ),
            )

        if filter_value is None and filter_key != SELECT_ONE_FILTER_KEY:
            output_message += '\nThe filter was not applied, because parameter "Filter Value" has an empty value.'

    except Exception as e:
        siemplify.LOGGER.error(
            f"Error executing action {LIST_MEMBERS_IN_GROUP_SCRIPT_NAME}."
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f"Error executing action {LIST_MEMBERS_IN_GROUP_SCRIPT_NAME}. Reason: {e}"
        )

    if list_of_groups_csv:
        siemplify.result.add_result_json(list_of_groups_csv)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
