from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)

from ..core.CBResponseManagerLoader import CBResponseManagerLoader

SCRIPT_NAME = "CBResponse - Isolate Host"
INTEGRATION_NAME = "CBResponse"
SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED
    failed_entities = []
    successful_entities = []

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root", input_type=str
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key", input_type=str
    )
    version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Version",
        input_type=float,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        param_name="Verify SSL",
        provider_name=INTEGRATION_NAME,
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # If no exception occur - then connection is successful
        manager = CBResponseManagerLoader.load_manager(
            version,
            api_root,
            api_key,
            siemplify.LOGGER,
            verify_ssl,
            ca_certificate_file,
        )

        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
        if target_entities:
            for entity in target_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    sensor = None
                    if entity.entity_type == EntityTypes.ADDRESS:
                        sensor = manager.get_sensor_by_ip(entity.identifier)
                    if entity.entity_type == EntityTypes.HOSTNAME:
                        sensor = manager.get_sensor_by_hostname(entity.identifier)
                    if not sensor:
                        siemplify.LOGGER.warn(
                            f"No sensor data was found for entity: {entity.identifier}"
                        )
                        continue
                    manager.isolate_host(sensor.sensor_document_id)
                    output_message += (
                        f"Isolated the following entity:{entity.identifier} \n"
                    )
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                except Exception as e:
                    output_message += f"Unable to isolate {entity.identifier}: \n"
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if not successful_entities:
                siemplify.LOGGER.info("\n No entities were processed.")
                output_message = "No entities were processed."
        else:
            output_message = "No suitable entities found.\n"
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
