from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from tanium.core.TaniumManager import TaniumManager
from tanium.core.exceptions import TaniumManagerException
from tanium.core.constants import (
    INTEGRATION_NAME,
    CREATE_CONNECTION_SCRIPT_NAME,
    ENTITY_TYPE_MAPPING,
)
from tanium.core.utils import get_entity_original_identifier


SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_CONNECTION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities, failed_entities = [], []
    json_results = {}
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]
    try:
        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
            try:
                entity_details = manager.get_endpoint_details(
                    entity_type=ENTITY_TYPE_MAPPING.get(entity.entity_type),
                    entity_identifier=entity_identifier,
                )
                if entity_details:
                    connection = manager.create_conection(
                        hostname=entity_details[0].hostname,
                        ip=entity_details[0].ip,
                        client_id=entity_details[0].client_id,
                        platform=entity_details[0].platform,
                    )
                    successful_entities.append(entity_identifier)
                    json_results[entity_identifier] = connection
                else:
                    siemplify.LOGGER.info(f"No details found for {entity_identifier}")
                    failed_entities.append(entity_identifier)
            except TaniumManagerException as err:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(err)
        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        if successful_entities:
            successful_entities_string = ", ".join(successful_entities)
            output_message += (
                f"Successfully created a connection for the following "
                f"entities: {successful_entities_string}\n"
            )
            result_value = True
        if failed_entities:
            failed_entities_string = ", ".join(failed_entities)
            output_message += (
                f"Action wasn't able to create a connection for the following "
                f"entities: {failed_entities_string}"
            )
        if not successful_entities and not failed_entities:
            output_message = "No suitable entities were found in the scope."
    except TaniumManagerException as e:
        output_message = (
            f"Error executing action {CREATE_CONNECTION_SCRIPT_NAME}. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nstatus: {status}\n"
        f"result_value: {result_value}\n"
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
