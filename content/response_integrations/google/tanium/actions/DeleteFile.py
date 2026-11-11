from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from tanium.core.TaniumManager import TaniumManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from tanium.core.constants import INTEGRATION_NAME, DELETE_FILE_SCRIPT_NAME, CONNECTED_STATUS
from tanium.core.utils import get_entity_original_identifier, convert_comma_separated_to_list
from time import sleep


SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_FILE_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
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
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    file_paths_string = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=False, print_value=True
    )
    file_paths = convert_comma_separated_to_list(file_paths_string)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""
    result_value = True

    try:
        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )
        open_connections = manager.get_open_connections()

        for entity in siemplify.target_entities:
            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                entity_identifier = get_entity_original_identifier(entity)
                entity_connections = [
                    connection
                    for connection in open_connections
                    if entity_identifier in [connection.ip, connection.hostname]
                ]

                if entity_connections:
                    enabled_connection = next(
                        (
                            connection
                            for connection in entity_connections
                            if connection.status == CONNECTED_STATUS
                        ),
                        None,
                    )
                    siemplify.LOGGER.info(f"Found connection for {entity.identifier}")

                    if not enabled_connection:
                        siemplify.LOGGER.info("Disabled. Creating connection... ")
                        manager.create_conection(
                            hostname=entity_connections[0].hostname,
                            ip=entity_connections[0].ip,
                            client_id=entity_connections[0].client_id,
                            platform=entity_connections[0].platform,
                        )
                        for i in range(3):
                            siemplify.LOGGER.info("Checking connection status... ")
                            sleep(5)
                            open_connections = manager.get_open_connections()
                            entity_connections = [
                                connection
                                for connection in open_connections
                                if entity_identifier
                                in [connection.ip, connection.hostname]
                            ]
                            enabled_connection = next(
                                (
                                    connection
                                    for connection in entity_connections
                                    if connection.status == CONNECTED_STATUS
                                ),
                                None,
                            )
                            if enabled_connection:
                                break
                        if not enabled_connection:
                            siemplify.LOGGER.info(
                                f"Connection was not enabled. Skipping entity {entity_identifier}."
                            )
                            failed_entities.append(entity)
                            continue
                        connection_id = enabled_connection.id
                    else:
                        connection_id = enabled_connection.id

                    successful_files = []
                    failed_files = []
                    siemplify.LOGGER.info(f"Deleting files for {entity.identifier}")
                    for file_path in file_paths:
                        try:
                            siemplify.LOGGER.info(f"Started deleting file: {file_path}")
                            manager.delete_file(
                                connection_id=connection_id, file_path=file_path
                            )
                            successful_files.append(file_path)
                            siemplify.LOGGER.info(
                                f"Successfully deleted file: {file_path}"
                            )
                        except Exception as e:
                            failed_files.append(file_path)
                            siemplify.LOGGER.error(
                                f"An error occurred on file {file_path}"
                            )
                            siemplify.LOGGER.exception(e)

                    json_results[entity.identifier] = {
                        "success": successful_files,
                        "not_exist_already_or_errors": failed_files,
                    }
                    if successful_files:
                        successful_entities.append(entity)
                    if failed_files:
                        missing_entities.append(entity)
                else:
                    siemplify.LOGGER.info(
                        f"No connection found for {entity.identifier}"
                    )
                    failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully deleted files from the following endpoints in {}:\n{}\n\n".format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if missing_entities:
            output_message += (
                "Status about some of the files is not clear, please check the JSON result. "
                "Tanium returns status code 500 in the case, when file is not found, but also, "
                "if there are some other challenges.\n\n"
            )

        if failed_entities:
            output_message += (
                "Action wasn't able to delete files from the following endpoints in {}:\n{}.\nPlease "
                "make sure that the Tanium Threat Response agent is connected properly and the "
                "hostname/IP address is correct.\n".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )
            )

        if not successful_entities:
            result_value = False

            if not failed_entities and missing_entities:
                output_message = (
                    "Status about all of the files is not clear, please check the JSON result. "
                    "Tanium returns status code 500 in the case, when file is not found, but also, "
                    "if there are some other challenges."
                )

            elif not missing_entities and failed_entities:
                output_message = (
                    "Action wasn't able to delete files from the provided endpoints in Tanium. Please "
                    "make sure that the Tanium Threat Response agent is connected properly and "
                    "the hostname/IP address is correct"
                )
            elif not missing_entities and not failed_entities:
                output_message = "No suitable entities were found in the scope."

        if successful_entities or missing_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f'Error executing action "{DELETE_FILE_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{DELETE_FILE_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
