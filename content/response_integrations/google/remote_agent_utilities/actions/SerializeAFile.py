from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_action_param
import os
import base64

INTEGRATION_NAME = "RemoteAgentUtilities"
SCRIPT_NAME = "Serialize A File"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 10MB


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    file_path = extract_action_param(
        siemplify,
        param_name="File Path",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        if not os.path.exists(file_path):
            output_message = f"{file_path} doesn't exist or is not accessible."
            siemplify.LOGGER.error(output_message)
            siemplify.end(output_message, "false", EXECUTION_STATE_FAILED)

        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            output_message = (
                f"{file_path} is bigger than {MAX_FILE_SIZE / (1024 * 1024)}MB."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.end(output_message, "false", EXECUTION_STATE_FAILED)

        file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            siemplify.LOGGER.info(f"Reading content from {file_path}")
            file_content = f.read()

            json_results = {
                "base64_file_content": base64.b64encode(file_content.encode("utf-8")),
                "file_name": file_name,
            }
            output_message = f"Successfully serialized {file_path}"

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
