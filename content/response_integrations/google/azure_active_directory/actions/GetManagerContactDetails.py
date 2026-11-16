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
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
    output_handler,
)
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv
from ..core.constants import INTEGRATION_NAME, GET_MANAGER_CONTACT_DETAILS_SCRIPT_NAME, USER_MANAGER_TABLE_NAME, DEFAULT_API_ROOT, DEFAULT_LOGIN_API_ROOT
from ..core.utils import get_entity_original_identifier, convert_comma_separated_to_list
from ..core.exceptions import AzureADNotFoundError

SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_MANAGER_CONTACT_DETAILS_SCRIPT_NAME
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
    include_mfa_details = extract_action_param(
        siemplify,
        param_name="Include MFA Details",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    include_last_sign_in_details = extract_action_param(
        siemplify,
        param_name="Include Last Sign In Details",
        print_value=True,
        input_type=bool,
        default_value=True,
    )

    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    json_results, successful_entities, failed_entities, not_found_entities = (
        {},
        [],
        [],
        [],
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if fields_to_return:
            fields_to_return = convert_comma_separated_to_list(fields_to_return)

        manager = AzureADManager(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            verify_ssl=verify_ssl,
            api_root=api_root,
            login_api_root=login_api_root,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

            try:
                user_manager = manager.get_users_manager(
                    user_principal_name=entity_identifier,
                    fields_to_return=fields_to_return
                )

                if include_mfa_details:
                    manager.enrich_manager_with_mfa(
                        user_principal_name=entity_identifier,
                        user_manager=user_manager,
                        logger=siemplify.LOGGER
                    )

                if include_last_sign_in_details:
                    sign_in_activity_user = manager.get_user(
                        user_principal_name=user_manager.userid,
                        fields_to_return="signInActivity"
                    )
                    user_manager.set_signin_details(
                        sign_in_activity_user.raw_data.get("signInActivity", {})
                    )

                successful_entities.append(entity_identifier)
                json_results[entity_identifier] = user_manager.to_json()
                siemplify.result.add_data_table(
                    title=USER_MANAGER_TABLE_NAME.format(entity_identifier),
                    data_table=construct_csv([user_manager.to_csv()]),
                )
            except AzureADNotFoundError as e:
                not_found_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

        if successful_entities:
            output_message = (
                f"Successfully processed entities: \n{', '.join(successful_entities)}\n"
            )

            if failed_entities:
                output_message += (
                    f"Failed processing entities: \n{', '.join(failed_entities)}\n"
                )

            if not_found_entities:
                output_message += f"Failed to get manager for the following entities:\n{', '.join(not_found_entities)}\n"

        else:
            output_message = "There are no entities containing manager contact details."
            result_value = False

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_MANAGER_CONTACT_DETAILS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"An error occurred while running action: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
