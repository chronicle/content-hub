from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_WORKBENCH_ALERT_SCRIPT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_WORKBENCH_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration parameters
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
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = False
    action_status = EXECUTION_STATE_FAILED

    try:
        if status == "Select One":
            raise Exception(
                "Please specify a valid 'Status' value to be set in Workbench Alert"
            )

        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        manager.update_alert(alert_id=alert_id, status=status)
        alert = manager.get_alert_by_id(alert_id=alert_id)

        result = True
        action_status = EXECUTION_STATE_COMPLETED
        output_message = f'Successfully updated workbench alert  with ID "{alert_id}" in {INTEGRATION_DISPLAY_NAME}.'
        siemplify.result.add_result_json(alert.to_json())

    except Exception as e:
        output_message = f'Error executing action "{UPDATE_WORKBENCH_ALERT_SCRIPT_NAME}". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {action_status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, action_status)


if __name__ == "__main__":
    main()
