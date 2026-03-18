from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    ENRICH_IOCS_SCRIPT_NAME,
    NO_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.cyjax_exceptions import CyjaxException
from ..core.datamodels import EnrichedIOC
from ..core.utils import (
    get_entity_objects,
    get_integration_params,
    remove_ioc_enrichment,
)


def get_entity_resp(entity, entity_results):
    entity_resp = {}
    for result in entity_results:
        if result.get("ioc") == entity.identifier:
            entity_resp = {
                "Entity": entity.identifier,
                "EntityResult": {k: v for k, v in result.items() if k != "ioc"},
            }
            return entity_resp
    return entity_resp


@output_handler
def main():
    """Execute Enrich IOCs action for Cyjax.

    This action enriches Indicators of Compromise (IOCs) using Cyjax threat intelligence.
    It accepts entities of type domain, email, and IP address from the case and enriches
    them with threat intelligence data including GeoIP, ASN, and sightings information.

    Action Parameters:
        None (uses case entities)

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing enrichment results
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        CyjaxException: If API calls to Cyjax fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_token, verify_ssl = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE
    json_results = []

    try:
        entity_objects = get_entity_objects(siemplify)

        if not entity_objects:
            output_message = NO_ENTITIES_ERROR
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(json.dumps(json_results, indent=4))
            siemplify.end(output_message, result_value, status)
            return

        siemplify.LOGGER.info("Initializing Cyjax API client")
        cyjax_manager = APIManager(siemplify=siemplify, api_token=api_token, verify_ssl=verify_ssl)

        siemplify.LOGGER.info("Starting IOC enrichment")
        processed_data = cyjax_manager.process_enrich_iocs(entity_objects)
        enriched_results = processed_data["enriched_results"]
        failed_iocs = processed_data["failed_iocs"]
        not_found_iocs = processed_data["not_found_iocs"]

        csv_output = []
        successful_entities = []

        for entity in entity_objects:
            entity_identifier = entity.identifier
            if entity_identifier in failed_iocs or entity_identifier in not_found_iocs:
                continue

            entity_resp = get_entity_resp(entity, enriched_results)
            entity_datamodel = EnrichedIOC(
                entity_resp.get("EntityResult"), entity_resp.get("Entity")
            )
            entity_enrichment_data = entity_datamodel.get_entity_enrichment()
            entity_csv_output = entity_datamodel.to_csv()

            # Remove old Cyjax enrichment data
            remove_ioc_enrichment(entity)
            siemplify.LOGGER.info(f"Removed old enrichment data for {entity_identifier}")
            entity.additional_properties.update(entity_enrichment_data)
            entity.is_enriched = True
            json_results.append(entity_resp)

            successful_entities.append(entity)
            csv_output.append(entity_csv_output)

        if successful_entities:
            siemplify.update_entities(successful_entities)

        if json_results:
            output_message = f"Successfully enriched {len(json_results)} IOCs."
            if csv_output:
                siemplify.result.add_data_table("Enriched IOCs", construct_csv(csv_output), "Cyjax")
        else:
            output_message = "No IOCs were successfully enriched."
        if failed_iocs:
            output_message += f" Failed to enrich {len(failed_iocs)} IOCs."
        if not_found_iocs:
            output_message += f" {len(not_found_iocs)} IOCs were not found in Cyjax."

    except (CyjaxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ENRICH_IOCS_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json.dumps(json_results, indent=4))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
