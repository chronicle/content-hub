from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.SolarWindsOrionConstants import (
    PROVIDER_NAME,
    ENRICH_ENDPOINT_SCRIPT_NAME,
    ENRICHMENT_QUERY,
    DEFAULT_IP_KEY,
    DEFAULT_DISPLAY_NAME_KEY,
    ENRICHMENT_PREFIX,
)
from TIPCommon import extract_configuration_param
from ..core.SolarWindsOrionManager import SolarWindsOrionManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.SolarWindsOrionExceptions import FailedQueryException

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENDPOINT_SCRIPT_NAME
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_messages = []
    json_results = []
    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configurations
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="IP Address",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = SolarWindsOrionManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if suitable_entities:
            query = manager.build_entity_query(
                query_string=ENRICHMENT_QUERY,
                entities=suitable_entities,
                ip_key=DEFAULT_IP_KEY,
                hostname_key=DEFAULT_DISPLAY_NAME_KEY,
            )

            query_results = manager.execute_query(query=query)

            for entity in suitable_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                result = next(
                    (
                        r
                        for r in query_results
                        if entity.identifier in [r.ip_address, r.display_name]
                    ),
                    None,
                )
                if result:
                    enrichment_data = result.to_enrichment_data(
                        prefix=ENRICHMENT_PREFIX
                    )
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True
                    json_results.append(result)
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Successfully enriched the following entity from SolarWinds Orion: {entity. identifier}"
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Action was not able to enrich the following entity from SolarWinds Orion: {entity.identifier}"
                    )
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                {"results": [result.to_json() for result in json_results]}
            )
            output_messages.append(
                "Successfully enriched the following endpoints from SolarWinds Orion: \n {}".format(
                    "\n".join([entity.identifier for entity in successful_entities])
                )
            )

        if failed_entities:
            output_messages.append(
                "Action was not able to enrich the following endpoints from SolarWinds Orion: \n "
                "{}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        output_message = "\n".join(output_messages)

        if not successful_entities:
            output_message = "No entities were enriched."
            result_value = False

    except FailedQueryException as e:
        output_message = (
            "Action wasn't able to successfully execute query and retrieve results from SolarWinds "
            "Orion. Reason: {}".format(e)
        )
        result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich Endpoint". Reason: {e}'
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
