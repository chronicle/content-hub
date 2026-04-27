from __future__ import annotations
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    unix_now,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from TIPCommon import extract_configuration_param, construct_csv
from ..core.CBResponseManagerLoader import CBResponseManagerLoader

INTEGRATION_NAME = "CBResponse"
SCRIPT_NAME = "CBResponse - Enrich Process"
ENTITY_TABLE_HEADER = "Processes"
PREFIX = "CB_RESPONSE"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    failed_entities = []
    successful_entities = []
    json_results = {}
    all_processes = []

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
    process_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.PROCESS
    ]
    host_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
    ]
    try:
        manager = CBResponseManagerLoader.load_manager(
            version,
            api_root,
            api_key,
            siemplify.LOGGER,
            verify_ssl,
            ca_certificate_file,
        )
        if process_entities:
            for entity in process_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    processes = manager.get_process_by_name(entity.identifier)
                    if processes:
                        for index, process in enumerate(processes):
                            all_processes.append(process)
                            entity.additional_properties.update(
                                process.to_csv(f"{PREFIX}_{str(index)}")
                            )
                        entity.is_enriched = True
                        json_results[entity.identifier] = [
                            process.to_json() for process in processes
                        ]

                        output_message += (
                            f"The following entity was fetched: {entity.identifier} \n"
                        )
                        successful_entities.append(entity)
                        siemplify.LOGGER.info(
                            f"Finished processing entity:{entity.identifier}"
                        )
                    else:
                        siemplify.LOGGER.warn(
                            f"No processes were found: {entity.identifier}"
                        )
                except Exception as e:
                    output_message += f"Unable to fetch entity {entity.identifier} \n"
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"Failed processing entity:{entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

            for host_entity in host_entities:
                processes_for_host = [
                    process
                    for process in all_processes
                    if process.is_hostname_equal(host_entity)
                ]
                if processes_for_host:
                    siemplify.result.add_entity_table(
                        ENTITY_TABLE_HEADER,
                        construct_csv(
                            [process.to_csv() for process in processes_for_host]
                        ),
                    )

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

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
