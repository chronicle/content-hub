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
from ..core.FireEyeHelixConstants import PROVIDER_NAME, ADD_ENTITIES_TO_A_LIST
from ..core.FireEyeHelixExceptions import FireEyeHelixNotFoundListException
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.UtilsManager import get_item_type_and_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ENTITIES_TO_A_LIST
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = {}
    successful_entities = []
    failed_entities = []

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Init Integration Configurations
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", is_mandatory=True
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    # Init Action Parameters
    short_name = extract_action_param(
        siemplify, param_name="List Short Name", is_mandatory=True, print_value=True
    )
    risk = extract_action_param(
        siemplify, param_name="Risk", is_mandatory=False, print_value=True
    )
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        shot_list = manager.get_list_by_short_name(short_name)

        for entity in siemplify.target_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {entity.identifier}"
                )
                item_type, value = get_item_type_and_value(entity)
                entity_report = manager.add_item_to_list(
                    shot_list.id, value, item_type, risk, note
                )

                json_results[entity.identifier] = entity_report.to_json()
                successful_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Successfully added the {entity.identifier} entity to list"
                )
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Something went wrong while adding {entity.identifier} entity to list"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += (
                "Successfully added the following entities to {provider_name} list with short name "
                '"{short_name}": \n {entities}'.format(
                    provider_name=PROVIDER_NAME,
                    short_name=short_name,
                    entities="\n ".join(
                        [entity.identifier for entity in successful_entities]
                    ),
                )
            )

        if failed_entities:
            output_message += (
                "\nAction was not able to add the following entities to the {provider_name} list with "
                'short name "{short_name}": \n {entities}'.format(
                    provider_name=PROVIDER_NAME,
                    short_name=short_name,
                    entities="\n ".join(
                        [entity.identifier for entity in failed_entities]
                    ),
                )
            )

        if not successful_entities:
            msg = '\nNo entities were added to the list with short name "{short_name}" in {provider_name}.'
            output_message += msg.format(
                provider_name=PROVIDER_NAME, short_name=short_name
            )
            result_value = False

    except FireEyeHelixNotFoundListException:
        output_message = (
            f'List with short name "{short_name}" was not found in {PROVIDER_NAME}.'
        )
        siemplify.LOGGER.info(output_message)
        result_value = False
    except Exception as e:
        output_message = f'Error executing action "Add Entities To a List". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
