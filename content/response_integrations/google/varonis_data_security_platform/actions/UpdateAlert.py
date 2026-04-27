from __future__ import annotations
import traceback

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    convert_comma_separated_to_list,
)

from ..core.VaronisDataSecurityPlatformManager import (
    VaronisDataSecurityPlatformManager,
    VaronisManagerException,
)
from ..core.VaronisDataSecurityPlatformConstants import INTEGRATION_IDENTIFIER

STATUS_ID_MAP = {"Open": 1, "Under Investigation": 2, "Closed": 3}

CLOSE_REASON_ID_MAP = {
    "Not Provided": None,
    "Resolved": 1,
    "Misconfiguration": 2,
    "Threat model disabled or deleted": 3,
    "Account misclassification": 4,
    "Legitimate activity": 5,
    "Other": 6,
}


@output_handler
def main():
    siemplify = SiemplifyAction()
    alert_ids = []

    # Configuration.
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        siemplify.LOGGER.info("Connecting to Varonis Data Security Platform.")
        manager = VaronisDataSecurityPlatformManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        siemplify.LOGGER.info("Connected successfully.")

        alert_guid = extract_action_param(
            siemplify, param_name="Alert GUID", is_mandatory=True, print_value=True
        )
        alert_status = extract_action_param(
            siemplify, param_name="Alert Status", is_mandatory=True, print_value=True
        )
        close_reason = extract_action_param(
            siemplify, param_name="Closing Reason", is_mandatory=False, print_value=True
        )

        alert_ids = convert_comma_separated_to_list(alert_guid)
        close_reason_id = CLOSE_REASON_ID_MAP[close_reason]

        if alert_status == "Select One":
            raise VaronisManagerException(400, "Specify alert status")

        if alert_status == "Closed" and close_reason_id is None:
            raise VaronisManagerException(400, "Close reason not specified")

        manager.update_alert(
            alert_ids=alert_ids,
            status_id=STATUS_ID_MAP[alert_status],
            close_reason_id=close_reason_id,
        )
        output_message = f"Alert(s) {', '.join(alert_ids)} were updated successfully"
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

    except VaronisManagerException as ve:
        # if error in not fatal
        if 401 < ve.status_code < 500 or ve.status_code == 400:
            log_message = f"Failed to update alert(s) {', '.join(alert_ids)} due to following error: {ve}"
        else:
            log_message = f'Failed to execute "Update Alert" action! Error is {traceback.format_exc()}'
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(ve)
        output_message = log_message
        result_value = "false"
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        log_message = f'Failed to execute "Update Alert" action! Error is {traceback.format_exc()}'
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(e)
        output_message = log_message
        result_value = "false"
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
