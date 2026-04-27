from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IntsightsManager import IntsightsManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import (
    UserNotFoundError,
    AlertNotFoundError,
    ChangeAssigneeError,
    IntsightsGeneralError,
)
from ..core.consts import INTEGRATION_NAME, ASSIGN_ALERT_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ASSIGN_ALERT_ACTION
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
    assignee_id = extract_action_param(
        siemplify, param_name="Assignee ID", print_value=True
    )
    assignee_email = extract_action_param(
        siemplify, param_name="Assignee Email Address", print_value=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if not assignee_id and not assignee_email:
            raise IntsightsGeneralError(
                "Assignee ID or Email Address should be specified."
            )

        intsight_manager = IntsightsManager(
            server_address=api_root,
            account_id=account_id,
            api_key=api_key,
            api_login=False,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        if assignee_email and not assignee_id:
            assignee_id = intsight_manager.get_user_details(
                assignee_email=assignee_email
            )[0].get("_id")
            intsight_manager.assign_alert(alert_id=alert_id, assignee_id=assignee_id)
            output_message += (
                f"Successfully assigned analyst with email address {assignee_id} to the alert with ID"
                f" {alert_id} in {INTEGRATION_NAME}"
            )
        else:
            intsight_manager.assign_alert(alert_id=alert_id, assignee_id=assignee_id)
            output_message += (
                f"Successfully assigned analyst with ID {assignee_id} to the alert with ID {alert_id} "
                f"in {INTEGRATION_NAME}"
            )

    except UserNotFoundError as e:
        output_message += (
            "Action was not able to change the assignment on the alert with ID {}. Reason: Assignee "
            "with email address {} was not found.".format(alert_id, assignee_email)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except AlertNotFoundError as e:
        output_message += (
            "Action was not able to change the assignment on the alert with ID {}. Reason: Assignee "
            "with ID {} was not found.".format(alert_id, assignee_id)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except ChangeAssigneeError as e:
        output_message += f"Action was not able to change the assignment on the alert with ID {alert_id}. Reason: {e}."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except IntsightsGeneralError as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except Exception as e:
        output_message += f"Error executing action {ASSIGN_ALERT_ACTION}. Reason: {e}"
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
