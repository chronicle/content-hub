from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EasyVistaManager import EasyVistaManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.EasyVistaExceptions import EasyVistaInternalError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import INTEGRATION_NAME, ADD_COMMENT_TO_TICKET


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_TICKET
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
        siemplify, param_name="Comment", is_mandatory=True, input_type=str
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        easyvista_manager = EasyVistaManager(
            api_root=api_root,
            account_id=account_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        easyvista_manager.add_comment(account_id, ticket_identifier, comment)
        output_message = (
            f"Successfully added a comment to the EasyVista ticket {ticket_identifier}."
        )

    except EasyVistaInternalError as e:
        output_message = f"Failed to add a comment to the EasyVista ticket {ticket_identifier}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    except Exception as e:
        output_message = f"Error executing action {ADD_COMMENT_TO_TICKET}. Reason: {e}"
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
