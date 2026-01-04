from __future__ import annotations
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    get_domain_from_entity,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SpyCloudManager import SpyCloudManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_ENTITY_BREACHES_SCRIPT_NAME,
    DEFAULT_LIMIT,
    IPS_BREACH_TYPE,
    EMAILS_BREACH_TYPE,
    DOMAINS_BREACH_TYPE,
    USERNAMES_BREACH_TYPE,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.UtilsManager import get_timestamps, is_valid_email


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.USER, EntityTypes.URL]
ENRICHMENT_PREFIX = "SpyCloud"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITY_BREACHES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    catalog_filter = extract_action_param(siemplify, param_name="Catalog Filter", print_value=True)
    timeframe = extract_action_param(
        siemplify, param_name="Time Frame", is_mandatory=True, print_value=True
    )
    start_time_string = extract_action_param(siemplify, param_name="Start Time", print_value=True)
    end_time_string = extract_action_param(siemplify, param_name="End Time", print_value=True)
    limit = extract_action_param(
        siemplify,
        param_name="Max Breaches To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if limit < 0:
            raise Exception('"Max Breaches To Return" should be a positive number.')

        start_time, end_time = get_timestamps(timeframe, start_time_string, end_time_string)

        manager = SpyCloudManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        catalogs = (
            manager.get_catalogs(
                filter_value=catalog_filter, start_time=start_time, end_time=end_time
            )
            if catalog_filter
            else []
        )
        filtered_catalog = next(
            (catalog for catalog in catalogs if catalog.title == catalog_filter), None
        )
        catalog_id = filtered_catalog.id if filtered_catalog else None

        if catalog_filter and not catalog_id:
            raise Exception(
                f"Catalog {catalog_filter} was not found in SpyCloud. Please check the spelling."
            )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            try:
                if entity.entity_type == EntityTypes.ADDRESS:
                    breach_type = IPS_BREACH_TYPE
                elif entity.entity_type == EntityTypes.USER:
                    breach_type = (
                        EMAILS_BREACH_TYPE
                        if is_valid_email(entity.identifier)
                        else USERNAMES_BREACH_TYPE
                    )
                else:
                    breach_type = DOMAINS_BREACH_TYPE

                entity_identifier = (
                    get_domain_from_entity(entity)
                    if entity.entity_type == EntityTypes.URL
                    else entity.identifier
                )

                breaches = manager.get_breaches(
                    breach_type=breach_type,
                    breach_identifier=entity_identifier,
                    catalog_id=catalog_id,
                )
                breaches = breaches[:limit]

                if breaches:
                    successful_entities.append(entity)
                    json_results[entity.identifier] = [breach.to_json() for breach in breaches]
                    entity.additional_properties.update(
                        breaches[0].to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True
                else:
                    failed_entities.append(entity)

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entities: {entity.identifier}: Error is: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
            output_message += (
                "Successfully found breaches for the following entities in {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            )

        if failed_entities:
            output_message += "\nAction wasn’t able to find breaches for the following entities in {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result = False
            output_message = "No information about breaches was found for the provided entities."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_ENTITY_BREACHES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{LIST_ENTITY_BREACHES_SCRIPT_NAME}." Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
