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

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.MicrosoftConstants import (
    INTEGRATION_NAME,
    SEND_CHAT_MESSAGE_ACTION,
    INTEGRATION_DISPLAY_NAME,
    FILTER_KEY_SELECT_ONE_FILTER,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    NOT_SPECIFIED_FILTER,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEND_CHAT_MESSAGE_ACTION
    siemplify.LOGGER.info(f"----------------- Main - Param Init -----------------")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=True,
        print_value=False,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        print_value=True,
    )
    redirect_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Redirect URL",
        is_mandatory=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        is_mandatory=True,
        print_value=False,
    )
    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )

    chat_type = extract_action_param(
        siemplify, param_name="Chat Type", print_value=True, is_mandatory=False
    )
    filter_key = extract_action_param(
        siemplify, param_name="Filter Key", print_value=True, is_mandatory=False
    )
    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True, is_mandatory=False
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        print_value=True,
        is_mandatory=False,
        input_type=int,
        default_value=50,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        if limit is not None:
            if limit < 1:
                raise Exception(
                    f'Invalid value was provided for "Max Records to Return": {limit}. Positive number should be provided.'
                )

        if (
            (filter_logic == EQUAL_FILTER or filter_logic == CONTAINS_FILTER)
            and filter_key != FILTER_KEY_SELECT_ONE_FILTER
            and filter_value is None
        ):
            filter_key = FILTER_KEY_SELECT_ONE_FILTER
            filter_logic = NOT_SPECIFIED_FILTER
            output_message += 'The filter was not applied, because parameter "Filter Value" has an empty value. '

        if filter_key == FILTER_KEY_SELECT_ONE_FILTER and (
            filter_logic == EQUAL_FILTER or filter_logic == CONTAINS_FILTER
        ):
            raise Exception(
                f'you need to select a field from the "Filter Key" parameter.'
            )

        manager = MicrosoftTeamsManager(
            client_id=client_id,
            client_secret=secret_id,
            tenant=tenant,
            refresh_token=token,
            redirect_url=redirect_url,
            api_root=api_root,
            login_api_root=login_api_root,
            verify_ssl=verify_ssl,
        )
        list_of_chats = manager.get_chats(
            chat_type=chat_type,
            filter_key=filter_key,
            filter_value=filter_value,
            filter_logic=filter_logic,
            limit=limit,
        )

        if not list_of_chats:
            output_message += f"No chats were found for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
            result_value = False

        else:
            output_message += f"Successfully found chats for the provided criteria in {INTEGRATION_DISPLAY_NAME}."
            siemplify.result.add_result_json([chat.to_json() for chat in list_of_chats])
            siemplify.result.add_data_table(
                "Available Chats:",
                data_table=construct_csv([chat.to_table() for chat in list_of_chats]),
            )

    except Exception as err:
        output_message = (
            f"Error executing action {SEND_CHAT_MESSAGE_ACTION}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
