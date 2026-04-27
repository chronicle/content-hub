from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param
from ..core.VectraManager import VectraManager
from ..core.constants import INTEGRATION_NAME, ENRICH_ENDPOINT_SCRIPT_NAME, ENRICHMENT_PREFIX


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENDPOINT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    output_message = ""
    json_results = {}
    successful_entities = []
    failed_entities = []
    duplicate_entities = []

    try:
        vectra_manager = VectraManager(
            api_root, api_token, verify_ssl=verify_ssl, siemplify=siemplify
        )
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
            or entity.entity_type == EntityTypes.HOSTNAME
        ]

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            endpoints = vectra_manager.get_endpoint_details(
                entity.entity_type, entity.identifier
            )
            filtered_endpoints = [
                item
                for item in endpoints
                if item.name.lower() == entity.identifier.lower()
                or item.ip == entity.identifier
            ]
            if filtered_endpoints:
                endpoint = filtered_endpoints[0]
                enrichment_data = endpoint.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                entity.additional_properties.update(enrichment_data)
                entity.is_enriched = True

                # JSON result
                json_results[entity.identifier] = endpoint.to_json()
                siemplify.result.add_entity_table(entity.identifier, endpoint.to_csv())
                siemplify.LOGGER.info(
                    "Successfully enriched the following endpoint from Vectra:"
                    f" {entity.identifier}"
                )
                successful_entities.append(entity)
                if len(filtered_endpoints) > 1:
                    duplicate_entities.append(entity)
            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += (
                "Successfully enriched the following endpoints from Vectra: {}".format(
                    "\n".join([entity.identifier for entity in successful_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\n Action was not able to enrich the following"
                "endpoints from Vectra: {}".format(
                "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        if duplicate_entities:
            output_message += (
                "\n\n Multiple matches were found in Vectra,"
                " taking first match for the following "
                "entities: {}".format(
                    "\n".join([entity.identifier for entity in duplicate_entities])
                )
            )

        if not successful_entities:
            output_message = "No entities were enriched."
            result_value = "false"

    except Exception as e:
        output_message = f'Error executing action "Enrich Endpoint". Reason: {e}'
        result_value = "false"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
