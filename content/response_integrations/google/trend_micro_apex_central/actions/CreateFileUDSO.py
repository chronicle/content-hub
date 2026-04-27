from __future__ import annotations
import os

from TIPCommon import extract_configuration_param, extract_action_param

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from ..core.TrendMicroApexCentralManager import TrendMicroApexCentralManager
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
    CREATE_FILE_UDSO_SCRIPT_NAME,
    DEFAULT_SCAN_ACTION,
    UDSO_FILE_TYPE,
)
from ..core.exceptions import TrendMicroApexCentralPathError
from ..core.utils import load_csv_to_list, get_base64_string_of_file, get_sha1_of_file


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {CREATE_FILE_UDSO_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    application_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Application ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    file_paths = extract_action_param(
        siemplify, param_name="File Paths", is_mandatory=True, print_value=True
    )
    file_scan_action = extract_action_param(
        siemplify,
        param_name="Action",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_SCAN_ACTION,
    )
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=False, print_value=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""
    json_results = {}

    file_already_exists = []
    failed_paths = []
    failed_path_due_to_permissions = []
    successful_paths_to_sha1 = {}

    try:
        manager = TrendMicroApexCentralManager(
            api_root=api_root,
            application_id=application_id,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        file_paths = load_csv_to_list(file_paths, "File Paths")
        already_existing_udso_files = [
            udso.content for udso in manager.list_udso_entries(udso_type=UDSO_FILE_TYPE)
        ]

        for file_path in file_paths:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(f"Started processing file path: {file_path}")
                sha1_file = get_sha1_of_file(file_path)
                siemplify.LOGGER.info(f"SHA-1 of file: {sha1_file}")
                if sha1_file.upper() in map(str.upper, already_existing_udso_files):
                    file_already_exists.append(file_path)
                    continue

                manager.add_udso_file_to_list(
                    file_name=os.path.basename(file_path),
                    file_content_base64_string=get_base64_string_of_file(file_path),
                    file_scan_option=file_scan_action.upper(),
                    note=note,
                )
                successful_paths_to_sha1[file_path] = sha1_file.upper()
                siemplify.LOGGER.info(f"Finished processing file path: {file_path}")
            except TrendMicroApexCentralPathError as error:
                failed_path_due_to_permissions.append(file_path)
                siemplify.LOGGER.error(f"Failed to add UDSO based file of: {file_path}")
                siemplify.LOGGER.exception(error)

            except Exception as error:
                failed_paths.append(file_path)
                siemplify.LOGGER.error(f"Failed to add UDSO based file of: {file_path}")
                siemplify.LOGGER.exception(error)

        if file_already_exists:
            output_message = (
                "The following UDSO files already exist in {}:\n  {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(file_already_exists)
                )
            )
        if failed_path_due_to_permissions:
            output_message = "The following UDSO files were not found or were not accessible due to restricted permissions:\n    {}\n\n".format(
                "\n  ".join(failed_path_due_to_permissions)
            )

        if successful_paths_to_sha1:
            try:  # Retrieve json results for successfully added files
                siemplify.LOGGER.info(
                    f"Retrieving list of UDSO entries to fetch JSON results of added files"
                )
                listed_udso_entries = manager.list_udso_entries(
                    udso_type=UDSO_FILE_TYPE
                )
                for udso in listed_udso_entries:
                    if udso.content.upper() in successful_paths_to_sha1.values():
                        json_results[udso.content] = udso.to_json()
                if json_results:
                    siemplify.result.add_result_json(
                        convert_dict_to_json_result_dict(json_results)
                    )
            except Exception as error:
                siemplify.LOGGER.error(
                    f"Failed to list UDSO entities in order to retrieve json results for added files"
                )
                siemplify.LOGGER.exception(error)

            output_message += "Successfully created UDSO based on the following files in {}:\n  {}\n\n".format(
                INTEGRATION_DISPLAY_NAME, "\n  ".join(successful_paths_to_sha1.keys())
            )
            result_value = True

            if failed_paths:
                output_message += "Action wasn't able to create UDSO based on the following files in {}:\n  {}\n\n".format(
                    INTEGRATION_DISPLAY_NAME, "\n  ".join(failed_paths)
                )
        else:
            output_message += f"No UDSO were created in {INTEGRATION_DISPLAY_NAME}."

    except Exception as error:
        output_message = (
            f'Error executing action "{CREATE_FILE_UDSO_SCRIPT_NAME}". Reason: {error}.'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
