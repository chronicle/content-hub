from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyUtils import (
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
    unix_now,
)
from ..core.CBResponseManagerLoader import CBResponseManagerLoader
from TIPCommon import extract_configuration_param, construct_csv


INTEGRATION_NAME = "CBResponse"
SCRIPT_NAME = "CBResponse - List Processes"
SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = "true"
    successful_entities = []
    failed_entities = []
    json_results = {}

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

                    processes = manager.get_processes(sensor.sensor_document_id)
                    if not processes:
                        siemplify.LOGGER.warn(
                            f"No processes were found: {entity.identifier}"
                        )
                        continue
                    json_results[entity.identifier] = [
                        process.to_json() for process in processes
                    ]

                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv([process.to_csv() for process in processes]),
                    )

                    output_message += (
                        f"The following entity was fetched: {entity.identifier} \n"
                    )
                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity:{entity.identifier}"
                    )
                except Exception as e:
                    output_message += f"Unable to fetch entity {entity.identifier} \n"
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"Failed processing entity:{entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if successful_entities:
                siemplify.update_entities(successful_entities)
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
            else:
                siemplify.LOGGER.info("\n No entities were processed.")
                output_message += "No entities were processed."

        else:
            output_message = "No suitable entities found.\n"
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = "Some errors occurred. Please check log"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
