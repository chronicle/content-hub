from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import ADD_COMMENT_TO_MODEL_BREACH_NAME, INTEGRATION_NAME
from ..core.DarktraceExceptions import NotFoundException
from ..core.DarktraceManager import DarktraceManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_MODEL_BREACH_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
        print_value=True,
    )
    api_private_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Private Token",
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

    # Action parameters
    model_breach_id = extract_action_param(
        siemplify, param_name="Model Breach ID", is_mandatory=True, print_value=True
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Successfully added a comment to the alert with ID {model_breach_id} in Darktrace."
    )

    try:
        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        try:
            action_result = manager.add_comment_to_model_breach(
                model_breach_id=model_breach_id, comment=comment
            )
            siemplify.result.add_result_json(action_result)
        except NotFoundException:
            result = False
            status = EXECUTION_STATE_FAILED
            output_message = (
                f"Error executing action “Add Comment To Model Breach”.\n"
                f"Reason: model breach with ID {model_breach_id} wasn’t found in Darktrace.\n"
                f"Please check the spelling."
            )
    except Exception as critical_error:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action “Add Comment To Model Breach”. Reason: {critical_error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
