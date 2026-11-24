from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    DOWNLOAD_THREAT_FILE_SCRIPT_NAME,
    AFFECTED_STATUS,
)
from sentinel_one_v2.core.utils import save_fail
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory
from sentinel_one_v2.core.exceptions import SentinelOneV2AlreadyExistsError
import json
import sys
import os


def start_operation(
    siemplify, manager, threat_id, password, download_folder_path, overwrite
):
    """
    Main part of the action that creates the fetch job
    :param siemplify: SiemplifyAction object
    :param manager: SentinelOneV2 manager object
    :param threat_id: ID of the threat for which to download the file
    :param password: Password for the zip that contains the threat file
    :param download_folder_path: Path to the folder, where to store the threat file
    :param overwrite: If True, action will overwrite the file with the same name
    :return: {output message, json result, execution_state}
    """

    status = EXECUTION_STATE_COMPLETED

    is_affected = manager.create_fetch_job(threat_id, password)

    if is_affected == AFFECTED_STATUS:
        name, content = manager.get_file_from_timeline(threat_id)

        if name and content:
            absolute_file_path = save_fail(
                path=download_folder_path,
                name=name,
                content=content,
                overwrite=overwrite,
            )
            siemplify.result.add_result_json({"absolute_path": absolute_file_path})
            output_message = f"Successfully downloaded the file related to threat {threat_id} in SentinelOne"
            result_value = True
        else:
            status = EXECUTION_STATE_INPROGRESS
            output_message = "Waiting for the download link to appear in SentinelOne"
            result_value = json.dumps(threat_id)
    else:
        result_value = False
        output_message = (
            f"No files were found related to threat {threat_id} in SentinelOne"
        )

    return output_message, result_value, status


def query_operation_status(siemplify, manager, download_folder_path, overwrite):
    """
    Part of the action that periodically tries to fetch the threat file
    :param siemplify: SiemplifyAction object.
    :param manager: SentinelOneV2 manager object.
    :param download_folder_path: Path to the folder, where to store the threat file
    :param overwrite: If True, action will overwrite the file with the same name
    :return: {output message, json result, execution_state}
    """

    threat_id = json.loads(siemplify.extract_action_param("additional_data"))
    status = EXECUTION_STATE_COMPLETED
    name, content = manager.get_file_from_timeline(threat_id)

    if name and content:
        absolute_file_path = save_fail(
            path=download_folder_path, name=name, content=content, overwrite=overwrite
        )
        siemplify.result.add_result_json({"absolute_path": absolute_file_path})
        output_message = f"Successfully downloaded the file related to threat {threat_id} in SentinelOne"
        result_value = True
    else:
        status = EXECUTION_STATE_INPROGRESS
        output_message = "Waiting for the download link to appear in SentinelOne"
        result_value = json.dumps(threat_id)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_THREAT_FILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    threat_id = extract_action_param(
        siemplify, param_name="Threat ID", is_mandatory=True, print_value=True
    )
    password = extract_action_param(
        siemplify, param_name="Password", is_mandatory=True, print_value=False
    )
    download_folder_path = extract_action_param(
        siemplify,
        param_name="Download Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    overwrite = extract_action_param(
        siemplify,
        param_name="Overwrite",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root, api_token=api_token, verify_ssl=verify_ssl
        )

        # Raise an error if path does not exist
        if not os.path.exists(download_folder_path):
            raise Exception("Specified path doesn't exist.")

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager, threat_id, password, download_folder_path, overwrite
            )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify, manager, download_folder_path, overwrite
            )

    except SentinelOneV2AlreadyExistsError as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{DOWNLOAD_THREAT_FILE_SCRIPT_NAME}". Reason: file with path {e}'
            f' already exists. Please delete the file or set "Overwrite" to true.'
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {DOWNLOAD_THREAT_FILE_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{DOWNLOAD_THREAT_FILE_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
