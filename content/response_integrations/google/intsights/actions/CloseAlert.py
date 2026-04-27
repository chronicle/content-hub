from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IntsightsManager import IntsightsManager
from ..core.exceptions import AlertNotFoundError, IntsightsGeneralError
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import (
    INTEGRATION_NAME,
    CLOSE_ALERT_ACTION,
    MAX_RATE,
    MIN_RATE,
    REASON_MAPPING,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CLOSE_ALERT_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    account_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    additional_information = extract_action_param(
        siemplify, param_name="Additional Info", print_value=True
    )
    rate = extract_action_param(siemplify, param_name="Rate", input_type=int)
    reason = extract_action_param(
        siemplify,
        param_name="Reason",
        is_mandatory=True,
        default_value="Problem Solved",
        print_value=True,
    )
    reason = REASON_MAPPING.get(reason, "")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if rate and (rate < MIN_RATE or rate > MAX_RATE):
            raise IntsightsGeneralError(
                f"Rate value should be in range from {MIN_RATE} to {MAX_RATE}."
            )

        intsight_manager = IntsightsManager(
            server_address=api_root,
            account_id=account_id,
            api_key=api_key,
            api_login=False,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        intsight_manager.close_alert(
            alert_id=alert_id,
            reason=reason,
            additional_information=additional_information,
            rate=rate,
        )
        output_message = (
            f"Successfully closed the alert with ID {alert_id} in Intsights"
        )

    except AlertNotFoundError as e:
        output_message += f"Action was not able to close the alert with ID {alert_id} in Intsights. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except IntsightsGeneralError as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message += f"Error executing action {CLOSE_ALERT_ACTION}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
