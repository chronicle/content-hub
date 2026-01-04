from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    ADD_COMMENT_TO_ALERT_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
)
from ..core.OrcaSecurityManager import OrcaSecurityManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        alert_comment = manager.add_alert_comment(alert_id, comment)
        siemplify.result.add_result_json(alert_comment.to_json())
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = f'Successfully added a comment to alert with ID "{alert_id}" in {INTEGRATION_DISPLAY_NAME}'

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"General error performing action {ADD_COMMENT_TO_ALERT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{ADD_COMMENT_TO_ALERT_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
