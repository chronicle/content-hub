from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_action_param
import os
import base64

INTEGRATION_NAME = "RemoteAgentUtilities"
SCRIPT_NAME = "Deserialize A File"
AGENT_FOLDER = "/opt/SiemplifyAgent/Files/"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    file_content = extract_action_param(
        siemplify,
        param_name="File base64",
        is_mandatory=True,
        input_type=str,
        print_value=False,
    )
    file_name = extract_action_param(
        siemplify,
        param_name="File Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}
    status = EXECUTION_STATE_COMPLETED

    try:
        if not os.path.exists(AGENT_FOLDER):
            siemplify.LOGGER.info(f"Creating folder {AGENT_FOLDER}")
            os.makedirs(AGENT_FOLDER)

        new_file_path = os.path.join(AGENT_FOLDER, file_name)

        with open(new_file_path, "wb") as f:
            siemplify.LOGGER.info(f"Writing file content to {new_file_path}")
            f.write(base64.b64decode(file_content))
            output_message = f"Successfully deserialized file base 64. New file is available here: {new_file_path}"
            result_value = new_file_path

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = ""
        output_message = f"Action didn't complete due to error: {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
