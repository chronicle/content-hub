from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EasyVistaManager import EasyVistaManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.EasyVistaExceptions import EasyVistaInternalError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, CLOSE_EASYVISTA_TICKET, DATETIME_FORMAT
import datetime


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CLOSE_EASYVISTA_TICKET
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root"
    )
    account_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Account ID"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    ticket_identifier = extract_action_param(
        siemplify, param_name="Ticket Identifier", is_mandatory=True, input_type=str
    )
    comment = extract_action_param(
        siemplify, param_name="Comment", is_mandatory=False, input_type=str
    )
    actions_close_date = extract_action_param(
        siemplify, param_name="Actions Close Date", is_mandatory=False, input_type=str
    )
    delete_ongoing_actions = extract_action_param(
        siemplify,
        param_name="Delete ongoing actions?",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    # Check if the given timestamp is in the correct format
    if actions_close_date:
        try:
            datetime.datetime.strptime(actions_close_date, DATETIME_FORMAT)
        except ValueError:
            actions_close_date = ""
            output_message = "Given value for parameter: Actions Close Date is incorrect, we will use current time instead.\n"
            siemplify.LOGGER.error(
                "Given value for parameter: Actions Close Date is incorrect, we will use current time instead."
            )

    try:
        easyvista_manager = EasyVistaManager(
            api_root=api_root,
            account_id=account_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        easyvista_manager.close_ticket(
            account_id,
            ticket_identifier,
            comment,
            actions_close_date,
            delete_ongoing_actions,
        )
        output_message += f"Successfully closed EasyVista ticket {ticket_identifier}."

    except EasyVistaInternalError as e:
        output_message = (
            f"Failed to close EasyVista ticket {ticket_identifier}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except Exception as e:
        output_message = f"Error executing action {CLOSE_EASYVISTA_TICKET}. Reason: {e}"
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
