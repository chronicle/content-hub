from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from ..core.SymantecBlueCoatProxySGManager import SymantecBlueCoatProxySGManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    BLOCK_ENTITIES_SCRIPT_NAME,
    SUCCESS_TEXT,
    STATUS_SUCCESS,
    STATUS_FAILURE,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.UtilsManager import get_entity_original_identifier


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = BLOCK_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    ssh_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="SSH Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    not_found_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = SymantecBlueCoatProxySGManager(
            ssh_root=ssh_root,
            username=username,
            password=password,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
            entity_original_identifier = get_entity_original_identifier(entity)

            try:
                output = manager.block_entity(entity_original_identifier)

                if SUCCESS_TEXT in output:
                    json_results[entity.identifier] = {
                        "raw_output": output,
                        "status": STATUS_SUCCESS,
                    }
                    successful_entities.append(entity)
                else:
                    json_results[entity.identifier] = {
                        "raw_output": output,
                        "status": STATUS_FAILURE,
                    }
                    not_found_entities.append(entity)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entity: {entity.identifier}: Error is: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        if successful_entities:
            output_message += (
                "Successfully blocked the following entities in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            )

        if not_found_entities:
            output_message += "\nAction wasn't able to block the following entities in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in not_found_entities]),
            )

        if failed_entities:
            output_message += (
                "\nFailed to block the following entities in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )
            )

        if not successful_entities:
            result = False
            output_message = "None of the provided entities were blocked."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {BLOCK_ENTITIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {BLOCK_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
