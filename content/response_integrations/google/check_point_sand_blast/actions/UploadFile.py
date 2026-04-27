from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.SandBlastManager import SandBlastManager
from ..core import datamodels
from ..core import consts
import os
from TIPCommon import extract_configuration_param, extract_action_param

SCRIPT_NAME = "Upload File"
INTEGRATION_NAME = "CheckPointSandBlast"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    #  INIT ACTION PARAMETERS:
    file_paths = extract_action_param(
        siemplify, param_name="File Path", print_value=True, is_mandatory=True
    )
    te_enabled = extract_action_param(
        siemplify,
        param_name="Enable Threat Emulation feature",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    av_enabled = extract_action_param(
        siemplify,
        param_name="Enable AntiVirus feature",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    extraction_enabled = extract_action_param(
        siemplify,
        param_name="Enable Threat Extraction feature",
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    file_paths = [file_path.strip() for file_path in file_paths.split(",")]

    if len(file_paths) > consts.MAX_ALLOWED_FILE_PATHS:
        siemplify.LOGGER.info(
            f"Maximum of {consts.MAX_ALLOWED_FILE_PATHS} files are allowed at a time. "
            f"Only first {consts.MAX_ALLOWED_FILE_PATHS} files will be uploaded."
        )
        file_paths = file_paths[: consts.MAX_ALLOWED_FILE_PATHS]

    features = []

    if te_enabled:
        features.append(datamodels.Features.THREAT_EMULATION)

    if av_enabled:
        features.append(datamodels.Features.ANTI_VIRUS)

    if extraction_enabled:
        features.append(datamodels.Features.THREAT_EXTRACTION)

    if not features:
        siemplify.LOGGER.info(
            "No features were selected. Threat emulation will be enabled by default."
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    successful_paths = []
    json_results = {}
    failed_paths = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"

    try:
        manager = SandBlastManager(api_root, api_key, verify_ssl)

        for file_path in file_paths:
            if not os.path.exists(file_path):
                siemplify.LOGGER.info(
                    f"File {file_path} doesn't exist or inaccessible. Skipping."
                )
                continue

            elif os.path.getsize(file_path) > consts.MAX_ALLOWED_FILE_SIZE_BYTES:
                siemplify.LOGGER.info(
                    f"File {file_path} exceeds size limit of "
                    f"{consts.MAX_ALLOWED_FILE_SIZE_MB}MB. Skipping."
                )
                continue

            siemplify.LOGGER.info(f"Uploading {file_path}")
            file_name = os.path.basename(file_path)
            query_response = manager.upload_file(file_path, file_name, features)
            siemplify.LOGGER.info(
                f"File uploaded with status {query_response.status.label}"
            )

            if manager.is_successful_upload(query_response):
                successful_paths.append(file_path)

            else:
                siemplify.LOGGER.info(
                    f"Upload status message: {query_response.status.message}"
                )
                failed_paths.append(file_path)

            json_results[file_path] = query_response.raw_data

        if successful_paths:
            output_message = (
                "Successfully uploaded the following files:\n   {}\n\n".format(
                    "\n   ".join([file_path for file_path in successful_paths])
                )
            )
            result_value = "true"

        else:
            output_message = "No files were uploaded.\n\n"

        if failed_paths:
            output_message += (
                "An error occurred on the following files:\n   {}\n\nPlease check logs "
                "for more information."
            ).format(
                "\n   ".join([file_path for file_path in failed_paths])
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
