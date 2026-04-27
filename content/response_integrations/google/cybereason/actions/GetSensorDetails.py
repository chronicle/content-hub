from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    add_prefix_to_dict,
    construct_csv,
)
from ..core.constants import (
    INTEGRATION_NAME,
    GET_SENSOR_DETAILS_SCRIPT_NAME,
    IP_SENSOR_KEY,
    HOSTNAME_SENSOR_KEY,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]
ENRICHMENT_PREFIX = "Cybereason_sensor"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SENSOR_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}
    result_value = True
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                siemplify.LOGGER.info(
                    f"Fetching sensor details for {entity_identifier}"
                )
                field_name = (
                    IP_SENSOR_KEY
                    if entity.entity_type == EntityTypes.ADDRESS
                    else HOSTNAME_SENSOR_KEY
                )
                sensor = manager.get_sensor_details(entity_identifier, field_name)

                if sensor:
                    siemplify.result.add_entity_table(
                        entity_identifier, construct_csv([sensor.to_csv()])
                    )
                    entity.additional_properties.update(
                        add_prefix_to_dict(
                            sensor.as_enrichment_data(), ENRICHMENT_PREFIX
                        )
                    )
                    json_results[entity_identifier] = sensor.to_json()
                    entity.is_enriched = True
                    successful_entities.append(entity)
                    if create_insight:
                        siemplify.add_entity_insight(entity, sensor.to_insight())
                else:
                    failed_entities.append(entity_identifier)
                siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = (
                f"Successfully found sensor information in {INTEGRATION_NAME} for the following entities: "
                f'{", ".join([get_entity_original_identifier(entity) for entity in successful_entities])}\n'
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to find sensor information in {INTEGRATION_NAME} for the "
                    f'following entities: {", ".join(failed_entities)}\n'
                )
        else:
            output_message = f"No sensor information was found for the provided entities in {INTEGRATION_NAME}."
            result_value = False

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_SENSOR_DETAILS_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
