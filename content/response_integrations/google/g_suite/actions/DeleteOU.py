from __future__ import annotations
from TIPCommon.extraction import extract_action_param

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, DELETE_OU_SCRIPT_NAME
from g_suite.core.exceptions import GSuiteValidationException
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {DELETE_OU_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    customer_id = extract_action_param(
        siemplify, param_name="Customer ID", is_mandatory=True, print_value=True
    )
    ou_path = extract_action_param(
        siemplify, param_name="OU Path", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        gsuite_manager = create_api_client(siemplify)
        gsuite_manager.delete_ou(customer_id=customer_id, path=ou_path)
        output_message = (
            "Successfully deleted organization unit for customer id"
            f"{customer_id} with organization unit path {ou_path}"
        )
    except GSuiteValidationException as error:
        output_message = (
            f"Error executing action {DELETE_OU_SCRIPT_NAME}. Reason: "
            "Customer ID is invalid"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
    except Exception as error:
        output_message = (
            f"Error executing action {DELETE_OU_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
