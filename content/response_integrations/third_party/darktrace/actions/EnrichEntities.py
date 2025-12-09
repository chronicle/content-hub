from __future__ import annotations

from urllib.parse import urlparse

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import (
    construct_csv,
    extract_action_param,
    extract_configuration_param,
    flat_dict_to_csv,
)

from ..core.constants import (
    DEFAULT_MAX_HOURS_BACKWARDS,
    DEVICE_KEYS,
    ENRICH_ENTITIES_NAME,
    ENRICHMENT_PREFIX,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
)
from ..core.DarktraceManager import DarktraceManager
from ..core.datamodels import Device, EndpointDetails

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()
SUPPORTED_ENTITY_TYPES = [
    EntityTypes.ADDRESS,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
    EntityTypes.URL,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_NAME
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
        print_value=True,
    )
    api_private_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Private Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    create_endpoint_insight = extract_action_param(
        siemplify,
        param_name="Create Endpoint Insight",
        input_type=bool,
        print_value=True,
    )
    fetch_connection_data = extract_action_param(
        siemplify, param_name="Fetch Connection Data", input_type=bool, print_value=True
    )
    hours_backwards = extract_action_param(
        siemplify,
        param_name="Max Hours Backwards",
        input_type=int,
        default_value=DEFAULT_MAX_HOURS_BACKWARDS,
        print_value=True,
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
        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if hours_backwards < 1:
            siemplify.LOGGER.info(
                f"Max Hours Backwards must be greater than zero. The default value "
                f"{DEFAULT_MAX_HOURS_BACKWARDS} will be used"
            )
            hours_backwards = DEFAULT_MAX_HOURS_BACKWARDS

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            try:
                entity_data = None
                connection_data = None
                result_key = entity.identifier

                if entity.entity_type == EntityTypes.ADDRESS:
                    entity_data = manager.get_devices(DEVICE_KEYS.get("ip"), entity.identifier)

                    if not entity_data:
                        entity_data = manager.get_endpoint_details(
                            DEVICE_KEYS.get("ip"), entity.identifier
                        )
                elif entity.entity_type == EntityTypes.HOSTNAME:
                    device = manager.search_devices_by_hostname(entity.identifier)

                    if device and device.mac_address:
                        entity_data = manager.get_devices(
                            DEVICE_KEYS.get("mac"), device.mac_address
                        )
                    elif device and device.ip:
                        entity_data = manager.get_devices(DEVICE_KEYS.get("ip"), device.ip)
                elif entity.entity_type == EntityTypes.MACADDRESS:
                    entity_data = manager.get_devices(DEVICE_KEYS.get("mac"), entity.identifier)
                else:
                    domain = urlparse(entity.identifier).netloc or urlparse(entity.identifier).path

                    if domain:
                        result_key = domain
                        entity_data = manager.get_endpoint_details(
                            DEVICE_KEYS.get("hostname"), domain
                        )

                if entity_data and entity_data.raw_data:
                    if fetch_connection_data and getattr(entity_data, "did", None):
                        connection_data = manager.get_connection_data(
                            entity_data.did, hours_backwards
                        )

                    successful_entities.append(entity)
                    json_results[result_key] = entity_data.to_json()
                    entity.additional_properties.update(
                        entity_data.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True

                    siemplify.result.add_entity_table(
                        entity.identifier, flat_dict_to_csv(entity_data.to_table())
                    )

                    if isinstance(entity_data, EndpointDetails) and entity_data.devices:
                        siemplify.result.add_data_table(
                            title=f"{entity.identifier}: Interacted Devices",
                            data_table=construct_csv(entity_data.to_csv()),
                        )

                    if isinstance(entity_data, Device) and create_endpoint_insight:
                        siemplify.add_entity_insight(
                            entity,
                            entity_data.as_insight(entity.identifier),
                            triggered_by=INTEGRATION_DISPLAY_NAME,
                        )

                    if connection_data:
                        json_results[result_key].update({
                            "connection_data": connection_data.to_json()
                        })

                        siemplify.result.add_data_table(
                            title=f"{entity.identifier}: Connection Data",
                            data_table=construct_csv(connection_data.to_table()),
                        )
                else:
                    failed_entities.append(entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed processing entities: {entity.identifier}: Error is: {e}"
                )
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
            siemplify.update_entities(successful_entities)
            output_message += "Successfully enriched the following entities using {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            output_message += (
                "\nAction wasn't able to enrich the following entities using {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )
            )

        if not successful_entities:
            result = False
            output_message = "No entities were enriched"

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {ENRICH_ENTITIES_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {ENRICH_ENTITIES_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
