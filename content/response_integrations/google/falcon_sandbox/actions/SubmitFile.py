from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.FalconSandboxManager import FalconSandboxManager, FalconSandboxInvalidCredsError
from TIPCommon import extract_configuration_param, extract_action_param

SCRIPT_NAME = "Submit File"
INTEGRATION_NAME = "FalconSandbox"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        input_type=str,
    )
    key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )

    #  INIT ACTION PARAMETERS:
    file_paths = extract_action_param(
        siemplify, param_name="File Path", print_value=True, is_mandatory=True
    )
    environment_name = extract_action_param(
        siemplify,
        param_name="Environment",
        input_type=str,
        print_value=True,
        default_value="Linux (Ubuntu 16.04, 64 bit)",
    )

    file_paths = [file_path.strip() for file_path in file_paths.split(",")]
    environment_id = FalconSandboxManager.get_environment_id_by_name(environment_name)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    successful_paths = []
    json_results = {}
    failed_paths = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"

    try:
        manager = FalconSandboxManager(server_address, key)

        for file_path in file_paths:
            try:
                siemplify.LOGGER.info(
                    f"Submitting {file_path} for analysis with environment {environment_name}"
                )
                job_id, sha256 = manager.submit_file(file_path, environment_id)
                siemplify.LOGGER.info(
                    f"Successfully submitted {file_path}. Job id: {job_id}"
                )
                successful_paths.append(file_path)

                json_results[file_path] = {"job_id": job_id, "sha256": sha256}

            except FalconSandboxInvalidCredsError as e:
                raise

            except Exception as e:
                failed_paths.append(file_path)
                siemplify.LOGGER.error(f"An error occurred on file {file_path}")
                siemplify.LOGGER.exception(e)

        if successful_paths:
            output_message = (
                "Successfully submit the following files:\n   {}\n\n".format(
                    "\n   ".join([file_path for file_path in successful_paths])
                )
            )
            result_value = "true"

        else:
            output_message = "No files were submitted for analysis.\n\n"

        if failed_paths:
            output_message += "An error occurred on the following files:\n   {}\n\nPlease check logs for more information.".format(
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
