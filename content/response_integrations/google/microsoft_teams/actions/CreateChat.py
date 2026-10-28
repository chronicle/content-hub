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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict

from TIPCommon.extraction import extract_configuration_param

from ..core.MicrosoftConstants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    CREATE_CHAT_ACTION,
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager
from ..core.datamodels import UserCollection


SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_CHAT_ACTION
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_results = {}
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
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

        identifiers_list = [entity.identifier for entity in suitable_entities]
        users = UserCollection(
            manager.filter_users_by_name(
                user_names=identifiers_list,
                select_fields=["displayName", "mail", "id"]
            )
        ).to_dict()

        me = manager.check_account()

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            user_id = users.get(entity.identifier) or users.get(
                entity.identifier.casefold()
            )

            if user_id is not None:
                try:
                    chat = manager.create_chat([me.user_id, user_id])
                    json_results[entity.identifier] = chat.to_json()
                    successful_entities.append(entity)
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Failed processing entities: {entity.identifier}: Error is: {e}"
                    )
                    failed_entities.append(entity)
            else:
                siemplify.LOGGER.info(f"User not found: {entity.identifier}")
                not_found_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message = (
                "Successfully created chat with the following users in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            )

        if not_found_entities:
            output_message += "\nThe following users were not found in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in not_found_entities]),
            )

        if failed_entities:
            output_message += "\nAction wasn't able to create a chat with the following users in {}: \n{}.".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result_value = False

            if len(not_found_entities) == len(suitable_entities):
                output_message = f"None of the provided users were found in {INTEGRATION_DISPLAY_NAME}."
            elif len(failed_entities) == len(suitable_entities):
                output_message = (
                    f"Action wasn't able to create a chat with the provided users in "
                    f"{INTEGRATION_DISPLAY_NAME}."
                )

    except Exception as e:
        output_message = f"Error executing action {CREATE_CHAT_ACTION}. Reason: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(f"----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
