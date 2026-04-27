from __future__ import annotations
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from ..core.DigitalShadowsManager import DigitalShadowsManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyDataModel import EntityTypes

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "DigitalShadows"
SCRIPT_NAME = "DigitalShadows - EnrichHash"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key", input_type=str
    )

    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Secret",
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    successful_entities = []
    failed_entities = []
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    json_results = {}
    try:
        manager = DigitalShadowsManager(api_key, api_secret)
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.FILEHASH
        ]

        if target_entities:
            for entity in target_entities:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    hash_obj = manager.enrich_hash(entity.identifier)
                    successful_entities.append(entity)
                    json_results[entity.identifier] = hash_obj.to_json()
                    ## enrich the entity
                    siemplify.result.add_entity_table(
                        entity.identifier, hash_obj.to_csv()
                    )
                    siemplify.result.add_entity_link(entity.identifier, hash_obj.link)
                    entity.additional_properties.update(hash_obj.to_enrichment_data())
                    entity.is_enriched = True
                    ## end enrichment
                    siemplify.LOGGER.info(
                        f"Finished processing for entity {entity.identifier}"
                    )
                except Exception as e:
                    failed_entities.append(entity.identifier)
                    siemplify.LOGGER.error(
                        f"Failed processing entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
            if successful_entities:
                siemplify.update_entities(successful_entities)
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
                output_message += "Successfully enriched hashes:\n {0}\n".format(
                    "\n   ".join([entity.identifier for entity in successful_entities])
                )
                result_value = "true"
            else:
                siemplify.LOGGER.info("\n No entities were processed.")
                output_message += "No entities were processed.\n"
                result_value = "false"
            if failed_entities:
                output_message += "Failed to enrich hashes:\n {0}".format(
                    "\n".join(failed_entities)
                )
        else:
            output_message = "No suitable entities found.\n"
            result_value = "false"

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action 'Enrich Hash'. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
