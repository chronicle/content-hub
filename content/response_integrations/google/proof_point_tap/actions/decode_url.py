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
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import string_to_multi_value
from ..core import authentication_manager as auth_manager
from ..core.constants import DECODE_URL_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME, INTEGRATION_NAME
from ..core.proof_point_tap_manager import ApiParameters,proof_point_tap_manager
from ..core.utils import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = DECODE_URL_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    encoded_urls = string_to_multi_value(
        extract_action_param(siemplify, param_name="Encoded URLs", print_value=True)
    )
    create_url_entities = extract_action_param(
        siemplify, param_name="Create URL Entities", print_value=True, input_type=bool
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_result, successful_entities, failed_entities = [], [], []

    try:
        auth_params = auth_manager.SessionAuthenticationParameters(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        api_params = ApiParameters(api_root=api_root)
        session = auth_manager.get_authenticated_session(auth_params)
        manager = proof_point_tap_manager(
            session=session,
            api_parameters=api_params,
            force_check_connectivity=True,
        )

        target_entities = [
            get_entity_original_identifier(entity)
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.URL
        ]

        decoded_urls = manager.decode_urls(urls=target_entities + encoded_urls)

        for decoded_url in decoded_urls:
            if decoded_url.success:
                json_result.append(decoded_url.to_json())

                if create_url_entities and decoded_url.encoded_url in encoded_urls:
                    siemplify.add_entity_to_case(
                        entity_identifier=decoded_url.decoded_url,
                        entity_type=EntityTypes.URL,
                        is_internal=False,
                        is_suspicous=False,
                        is_enriched=False,
                        is_vulnerable=True,
                        properties={"is_new_entity": True},
                    )
                successful_entities.append(decoded_url.encoded_url)

            else:
                siemplify.LOGGER.info(
                    f"Error can not decode: {decoded_url.encoded_url}"
                )
                failed_entities.append(decoded_url.encoded_url)

        if successful_entities:
            siemplify.result.add_result_json(json_result)
            output_message += (
                f"Successfully decoded the following URLs in {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(successful_entities)} \n"
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to decode the following URLs in {INTEGRATION_DISPLAY_NAME}:"
                    f" {', '.join(failed_entities)} \n"
                )

        else:
            output_message = (
                f"None of the provided URLs were decoded in {INTEGRATION_DISPLAY_NAME}."
            )
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {DECODE_URL_SCRIPT_NAME}. Reason: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
