from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, flat_dict_to_csv
from forti_analyzer.core.FortiAnalyzerManager import FortiAnalyzerManager
from forti_analyzer.core.constants import INTEGRATION_NAME, ENRICH_ENTITIES_SCRIPT_NAME, ENRICHMENT_PREFIX
from forti_analyzer.core.UtilsManager import get_entity_original_identifier


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
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
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities, failed_entities = [], []
    json_result = {}
    manager = None

    try:
        manager = FortiAnalyzerManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                if entity.entity_type == EntityTypes.ADDRESS:
                    device = manager.get_device(ip=entity_identifier)
                else:
                    device = manager.get_device(hostname=entity_identifier)

                if device:
                    json_result[entity_identifier] = device.to_json()
                    siemplify.LOGGER.info(f"Enriching entity {entity_identifier}")
                    entity.additional_properties.update(
                        device.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True
                    siemplify.result.add_entity_table(
                        entity_identifier, flat_dict_to_csv(device.to_table())
                    )
                    successful_entities.append(entity)
                else:
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")
            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}."
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                f"Successfully enriched the following entities using information from "
                f"{INTEGRATION_NAME}: "
                f"{', '.join([get_entity_original_identifier(entity) for entity in successful_entities])}\n\n"
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using information from"
                    f" {INTEGRATION_NAME}: "
                    f"{', '.join([get_entity_original_identifier(entity) for entity in failed_entities])}\n"
                )
        else:
            output_message = "None of the provided entities were enriched."
            result_value = False

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        try:
            if manager:
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_NAME}"
                )
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
