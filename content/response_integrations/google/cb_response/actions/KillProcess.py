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
import itertools

SCRIPT_NAME = "CBResponse - KillProcess"
INTEGRATION_NAME = "CBResponse"


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

        processes = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.PROCESS
        ]
        hostnames = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.HOSTNAME
        ]

        combinations = list(itertools.product(hostnames, processes))
        siemplify.LOGGER.info(f"Generated {len(combinations)} combinations.")

        if combinations:
            for combination in combinations:
                hostname, process = combination
                siemplify.LOGGER.info(
                    f"Processing process {process.identifier}, hostname {hostname.identifier}."
                )
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    sensor = manager.get_sensor_by_hostname(hostname.identifier)
                    if not sensor:
                        siemplify.LOGGER.info(
                            f"No sensor data was found for process {process.identifier}, hostname {hostname.identifier}."
                        )
                        continue
                    siemplify.LOGGER.info(
                        f"Killing process {process.identifier} on host {hostname.identifier}."
                    )
                    manager.kill_process(sensor.sensor_document_id, process.identifier)
                    output_message += (
                        f"The following process has been killed:{process.identifier} \n"
                    )
                    successful_entities.append(combination)
                    siemplify.LOGGER.info(
                        f"Finished processing process {process.identifier} on host {hostname.identifier}"
                    )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Unable to kill process {process.identifier} on host {hostname.identifier}."
                    )
                    failed_entities.append(combination)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {process.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            if not successful_entities:
                siemplify.LOGGER.info("\n No entities were processed.")
                output_message = "No entities were processed."
        else:
            output_message = "No suitable combinations found.\n"

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
