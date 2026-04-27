from __future__ import annotations
from ..core.ArmisManager import ArmisManager
from ..core.consts import INTEGRATION_NAME, UPDATE_ALERT_STATUS, DEFAULT_STATUS

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.exceptions import ArmisBadRequestException, ArmisNotFoundException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {UPDATE_ALERT_STATUS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )

    alert_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        print_value=True,
        default_value=DEFAULT_STATUS,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    output_message = ""

    try:
        alert_id = extract_action_param(
            siemplify,
            param_name="Alert ID",
            is_mandatory=True,
            input_type=int,
            print_value=True,
        )

        manager = ArmisManager(
            api_root=api_root, api_secret=api_secret, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info(
            f"Updating status of alert with ID {alert_id} "
            f"from {INTEGRATION_NAME} service"
        )
        manager.update_alert_status(alert_id=alert_id, status=alert_status)
        siemplify.LOGGER.info(
            f"Successfully updated status of alert with ID {alert_id} "
            f"from {INTEGRATION_NAME} service"
        )

        result_value = True
        output_message += (
            f"Successfully updated status of the alert '{alert_id}'"
            f" to '{alert_status}' in {INTEGRATION_NAME}."
        )
        status = EXECUTION_STATE_COMPLETED

    except ArmisBadRequestException as error:
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Alert '{alert_id}' already has status '{alert_status}' "
            f"in {INTEGRATION_NAME}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except ArmisNotFoundException as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{UPDATE_ALERT_STATUS}'. "
            f"Reason: alert '{alert_id}' wasn't found in {INTEGRATION_NAME}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{UPDATE_ALERT_STATUS}'. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
