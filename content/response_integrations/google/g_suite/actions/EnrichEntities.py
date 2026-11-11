from __future__ import annotations
from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, ENRICH_ENTITIES_SCRIPT_NAME
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict

SUPPORTED_ENTITIES = [EntityTypes.USER]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ENRICH_ENTITIES_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    enriched_entities = []  # list of successfully enriched entities
    failed_entities = []
    json_results = {}

    try:
        gsuite_manager = create_api_client(siemplify)
        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue
            siemplify.LOGGER.info(f"Enriching entity {entity.identifier.strip()}")
            try:
                user = gsuite_manager.get_user(primary_email=entity.identifier.strip())
                siemplify.LOGGER.info(
                    f"Successfully enriched entity {entity.identifier.strip()}"
                )
                json_results[entity.identifier] = user.as_json()
                entity.is_enriched = True
                entity.additional_properties.update(user.as_enriched())
                enriched_entities.append(entity)

            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to enrich entity {entity.identifier}"
                    f"from {INTEGRATION_NAME}"
                )
                siemplify.LOGGER.exception(error)
                failed_entities.append(entity.identifier)

        if enriched_entities:
            output_message = "The following entities were enriched:\n   {}\n\n".format(
                "\n   ".join([entity.identifier for entity in enriched_entities])
            )
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        else:
            output_message = "No entities were enriched.\n\n"

        if failed_entities:
            formatted_entities = "\n   ".join(failed_entities)
            output_message += (
                "Action failed to enrich the following entities:"
                f"\n\n   {formatted_entities}\n"
            )

    except Exception as error:
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {error}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
