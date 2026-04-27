from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CyberintManager import CyberintManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_ALERT_SCRIPT_NAME,
    STATUS_MAPPING,
    CLOSURE_REASON_MAPPING,
    CLOSED_STATUS,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_ALERT_SCRIPT_NAME
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
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    alert_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    closure_reason = extract_action_param(
        siemplify, param_name="Closure Reason", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        alert_status = STATUS_MAPPING.get(alert_status)
        closure_reason = CLOSURE_REASON_MAPPING.get(closure_reason)

        if not alert_status:
            raise Exception(f'"Status" needs to be provided.')

        if alert_status == CLOSED_STATUS and not closure_reason:
            raise Exception(
                f'if "Status" is "Closed", then you need to provide "Closure Reason".'
            )

        manager = CyberintManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.update_alert(
            alert_id=alert_id,
            status=alert_status,
            closure_reason=closure_reason if alert_status == CLOSED_STATUS else None,
        )
        output_message = f'Successfully updated the alert with ID "{alert_id}" in {INTEGRATION_DISPLAY_NAME}'

    except Exception as e:
        output_message = (
            f"Error executing action {UPDATE_ALERT_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
