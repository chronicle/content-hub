from __future__ import annotations
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, construct_csv

INTEGRATION_NAME = "Office365CloudAppSecurity"
SCRIPT_NAME = "Office365CloudAppSecurity - Enrich Entities"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"
    output_message = ""
    json_results = {}

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    cloud_app_manager = Office365CloudAppSecurityManager(
        api_root=api_root, api_token=api_token
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        status = EXECUTION_STATE_COMPLETED
        failed_entities = []
        successful_entities = []

        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.USER:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                try:
                    entity_obj = cloud_app_manager.get_entity(entity.identifier)
                    # Enrich entity
                    entity.additional_properties.update(entity_obj.to_enrichment_data())
                    entity.is_enriched = True
                    # Fill json with every entity data
                    json_results[entity.identifier] = entity_obj.to_json()
                    # Add case wall table for entity
                    entity_table = construct_csv([entity_obj.to_table_data()])
                    siemplify.result.add_data_table(
                        title=f"{entity.identifier} Entity Table ",
                        data_table=entity_table,
                    )

                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
            else:
                siemplify.LOGGER.info(
                    f"The entity {entity.identifier} is not a type of {EntityTypes.USER}, skipping..."
                )
        if successful_entities:
            siemplify.update_entities(successful_entities)
            output_message += (
                f"Successfully enriched the following entities"
                f" using information from Microsoft Cloud App Security: "
                f"{', '.join([entity.identifier for entity in successful_entities])}\n"
            )

        if failed_entities:
            output_message += (
                f"Action wasn’t able to enrich the following entities "
                f"using information from Microsoft Cloud App Security: "
                f"{', '.join([entity.identifier for entity in failed_entities])}\n"
            )

        if not failed_entities and not successful_entities:
            output_message += "No entities were processed."
            result_value = "false"

    except Exception as e:
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"Status: {status}\nResult Value: {result_value}\nOutput Message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
