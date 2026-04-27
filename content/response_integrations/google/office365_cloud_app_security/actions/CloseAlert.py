from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Office365CloudAppSecurityManager import Office365CloudAppSecurityManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.Office365CloudAppSecurityCommon import Office365CloudAppSecurityCommon

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "Office365CloudAppSecurity"
SCRIPT_NAME = "Office365CloudAppSecurity - Close Alert"

TRUE_POSITIVE_STATE = "True Positive"
BENIGN_STATE = "Benign"
FALSE_POSITIVE_STATE = "False Positive"
NO_REASON_STRING = "No Reason"

REASON_MAPPING = {
    BENIGN_STATE: {
        "Actual Severity Is Lower": 2,
        "Other": 4,
        "Confirmed With End User": 5,
        "Triggered By Test": 6,
    },
    FALSE_POSITIVE_STATE: {
        "Not Of Interest": 0,
        "Too Many Similar Alerts": 1,
        "Alert Is Not Accurate": 3,
        "Other": 4,
    },
}

STATE_MAPPING = {
    "Benign": "close_benign",
    "False Positive": "close_false_positive",
    "True Positive": "close_true_positive",
}

STATE_RESPONSE_MAPPING = {
    "Benign": "closed_benign",
    "False Positive": "closed_false_positive",
    "True Positive": "closed_true_positive",
}


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED
    result = True

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    # INIT ACTION PARAMETERS:
    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", print_value=True, input_type=str
    )
    state = extract_action_param(
        siemplify,
        param_name="State",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    reason = extract_action_param(
        siemplify, param_name="Reason", print_value=True, input_type=str
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        cloud_app_common = Office365CloudAppSecurityCommon(siemplify.LOGGER)
        cloud_app_manager = Office365CloudAppSecurityManager(
            api_root=api_root, api_token=api_token, siemplify=siemplify
        )

        reason_id = None
        if state != TRUE_POSITIVE_STATE and reason != NO_REASON_STRING:
            reason_id = REASON_MAPPING.get(state).get(reason)
            if reason_id is None:
                error_msg = (
                    f'invalid value was selected in the "Reason" parameter for state "{state}". Valid '
                    f"values: No Reason, {cloud_app_common.convert_list_to_comma_string(list(REASON_MAPPING.get(state).keys()))}."
                )
                raise Exception(error_msg)

        cloud_app_manager.close_alert(
            alert_id=alert_id,
            state=STATE_MAPPING.get(state),
            reason_id=reason_id,
            comment=comment,
            response_key=STATE_RESPONSE_MAPPING.get(state),
        )
        output_message = f"Successfully closed alert with ID {alert_id} in Microsoft Cloud App Security."
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "Close Alert". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
