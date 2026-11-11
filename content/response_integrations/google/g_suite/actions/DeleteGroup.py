from __future__ import annotations
from TIPCommon.extraction import extract_action_param

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, DELETE_GROUP_SCRIPT_NAME
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {DELETE_GROUP_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    email_address = extract_action_param(
        siemplify, param_name="Group Email Address", is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_FAILED
    result_value = False

    try:
        gsuite_manager = create_api_client(siemplify)
        try:
            gsuite_manager.delete_group(email_address)
            output_message = f"{INTEGRATION_NAME} group deleted."
            result_value = True
        except Exception as error:
            output_message = (
                f"Action was not able to find {INTEGRATION_NAME} group for deletion."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        output_message = (
            f"Failed to connect to Google {INTEGRATION_NAME}! Error is: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
