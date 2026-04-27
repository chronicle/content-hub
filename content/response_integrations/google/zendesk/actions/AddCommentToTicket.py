from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param


INTEGRATION_NAME = "Zendesk"
ADD_COMMENT_TO_TICKET = "Add Comment To Ticket"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_TICKET
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    user_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Email Address",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Token",
        print_value=False,
        is_mandatory=True,
    )
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
        print_value=True,
    )

    ticket_id = extract_action_param(
        siemplify,
        param_name="Ticket ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    comment_body = extract_action_param(
        siemplify,
        param_name="Comment Body",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    author_name = extract_action_param(
        siemplify,
        param_name="Author Name",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    is_internal_note = extract_action_param(
        siemplify,
        param_name="Internal Note",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    is_internal_note = not is_internal_note

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        zendesk = ZendeskManager(user_email, api_token, server_address)
        comment = zendesk.add_comment_to_ticket(
            ticket_id=ticket_id,
            comment_body=comment_body,
            author_name=author_name,
            internal_note=is_internal_note,
        )

        if comment:
            output_message = (
                f"Ticket with id {ticket_id} was updated with comment: {comment_body}"
            )
        else:
            output_message = (
                f"There was a problem adding comment to ticket with id: {ticket_id}."
            )
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
