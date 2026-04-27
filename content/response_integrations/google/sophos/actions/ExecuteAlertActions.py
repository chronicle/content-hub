from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SophosManager import SophosManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    EXECUTE_ALERT_ACTIONS_SCRIPT_NAME,
    ACTION_TYPES_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_ALERT_ACTIONS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Action parameters
    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        print_value=True,
        is_mandatory=True,
        input_type=str,
    )
    action = extract_action_param(
        siemplify,
        param_name="Action",
        print_value=True,
        is_mandatory=True,
        input_type=str,
    )
    message = extract_action_param(
        siemplify,
        param_name="Message",
        print_value=True,
        is_mandatory=False,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    action = ACTION_TYPES_MAPPING.get(action)
    result = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = SophosManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            test_connectivity=True,
        )

        manager.execute_alert_action(alert_id=alert_id, action=action, message=message)
        output_message = (
            f"Successfully initiated execution of the action {action} "
            f"for the Alert with ID {alert_id} in {INTEGRATION_DISPLAY_NAME}"
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {EXECUTE_ALERT_ACTIONS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {EXECUTE_ALERT_ACTIONS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
