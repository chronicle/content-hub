from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CBResponseManagerLoader import CBResponseManagerLoader
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from TIPCommon import extract_configuration_param, construct_csv

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "CBResponse"
SCRIPT_NAME = "CBResponse - Hosts By Process"
SUPPORTED_ENTITY_TYPES = [EntityTypes.PROCESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"
    json_result = {}
    failed_entities = []
    successful_entities = []
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

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
                    sensors = manager.get_sensors_by_process(entity.identifier)
                    if not sensors:
                        siemplify.LOGGER.warn(
                            f"No sensor data was found for entity: {entity.identifier}"
                        )
                        continue

                    sensors_json = [sensor.to_json() for sensor in sensors]
                    json_result[entity.identifier] = sensors_json

                    # Attach as csv
                    siemplify.result.add_entity_table(
                        entity.identifier,
                        construct_csv([sensor.to_json() for sensor in sensors]),
                    )

                    output_message += f"Carbon Black Response - hosts was found for the following entity:{entity.identifier} \n"

                    successful_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )
                    pass
                except Exception as e:
                    output_message += (
                        f"Unable to fetch host {entity.identifier}: \n{e}\n"
                    )

                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if successful_entities:
                siemplify.update_entities(successful_entities)
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_result)
                )
            else:
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
